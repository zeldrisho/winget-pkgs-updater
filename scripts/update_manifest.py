#!/usr/bin/env python3
"""
Update WinGet manifest with new version and SHA256
Fetches existing manifest from microsoft/winget-pkgs, updates it, and creates PR
"""

import os
import re
import sys
import json
import yaml
import hashlib
import requests
import tempfile
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def check_existing_pr(package_id: str, version: str) -> bool:
    """
    Check if PR already exists for this package version.
    Returns True if OPEN or MERGED PR exists (should skip), False otherwise (should create).
    Note: CLOSED PRs are ignored - we can retry them.
    """
    try:
        title = f"New version: {package_id} version {version}"
        print(f"🔍 Checking for existing PRs: {title}")
        
        result = subprocess.run(
            [
                'gh', 'pr', 'list',
                '--repo', 'microsoft/winget-pkgs',
                '--search', f'"{title}" in:title',
                '--state', 'all',  # Check open, merged, and closed PRs
                '--json', 'number,title,state',
                '--limit', '10'
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            prs = json.loads(result.stdout)
            if prs:
                for pr in prs:
                    if title.lower() in pr['title'].lower():
                        state = pr['state']
                        state_emoji = "🟢" if state == "OPEN" else "🟣" if state == "MERGED" else "⚪"
                        
                        # Only skip for OPEN or MERGED PRs
                        if state in ["OPEN", "MERGED"]:
                            print(f"⏭️  {state_emoji} PR already exists: #{pr['number']} ({state})")
                            print(f"   Title: {pr['title']}")
                            print(f"   URL: https://github.com/microsoft/winget-pkgs/pull/{pr['number']}")
                            print(f"   Skipping - PR is {state}")
                            return True  # Skip - PR exists and is open/merged
                        else:
                            # CLOSED PR - we can retry
                            print(f"   ⚪ Found CLOSED PR: #{pr['number']}")
                            print(f"   URL: https://github.com/microsoft/winget-pkgs/pull/{pr['number']}")
                            print(f"   Will create new PR (closed PRs can be retried)")
        
        print("✅ No active PR found - will create new one")
        return False  # No active PR found - should create
        
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not check existing PRs: {e}")
        print("Continuing anyway...")
        return False  # Continue on error


def download_file(url: str, filepath: str) -> bool:
    """Download file from URL to filepath"""
    try:
        print(f"Downloading: {url}")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"Downloaded to: {filepath}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        return False


def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 hash of file"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest().upper()


def calculate_msix_signature_sha256(msix_path: str) -> Optional[str]:
    """
    Calculate SHA256 of MSIX signature using PowerShell.
    Returns None if calculation fails.
    """
    try:
        ps_script = f'''
$packagePath = "{msix_path}"
$sigPath = [System.IO.Path]::GetTempFileName()
$appxFile = Get-AppxPackage -Path $packagePath -PackageTypeFilter Bundle,Main,Resource | Select-Object -First 1
if ($appxFile) {{
    $signHash = (Get-AuthenticodeSignature $packagePath).SignerCertificate.GetCertHashString("SHA256")
    Write-Output $signHash
}} else {{
    # Alternative method: Extract signature from MSIX
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($packagePath)
    $sigFile = $zip.Entries | Where-Object {{ $_.FullName -eq "AppxSignature.p7x" }}
    if ($sigFile) {{
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($sigFile, $sigPath, $true)
        $sigHash = (Get-FileHash -Path $sigPath -Algorithm SHA256).Hash
        Write-Output $sigHash
    }}
    $zip.Dispose()
    Remove-Item $sigPath -ErrorAction SilentlyContinue
}}
'''
        
        result = subprocess.run(
            ['pwsh', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            sig_hash = result.stdout.strip().upper()
            print(f"Calculated SignatureSha256: {sig_hash}")
            return sig_hash
        else:
            print(f"Warning: Could not calculate SignatureSha256: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Warning: Error calculating SignatureSha256: {e}")
        return None


def fetch_github_file(repo: str, path: str, branch: str = "master") -> Optional[str]:
    """Fetch file content from GitHub"""
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def update_manifest_content(
    content: str, 
    version: str, 
    sha256: Optional[str] = None, 
    signature_sha256: Optional[str] = None,
    release_notes: Optional[str] = None,
    release_notes_url: Optional[str] = None
) -> str:
    """
    Update version and SHA256 in manifest content.
    
    Strategy:
    1. Extract old version from PackageVersion field
    2. Replace ALL occurrences of old version with new version
    3. Update SHA256 hashes if provided
    4. Update ReleaseDate to today
    5. Update ReleaseNotes and ReleaseNotesUrl if provided
    """
    
    # Extract old version from PackageVersion field
    old_version = None
    version_match = re.search(r'PackageVersion:\s*([\d\.]+)', content)
    if version_match:
        old_version = version_match.group(1)
        print(f"  Detected old version: {old_version}")
        print(f"  Updating to new version: {version}")
    
    # Replace ALL occurrences of old version with new version
    # This handles: PackageVersion, InstallerUrl, DisplayName, etc.
    if old_version and old_version != version:
        # Count occurrences before replacement
        count = content.count(old_version)
        print(f"  Found {count} occurrences of version {old_version}")
        
        # Replace all occurrences
        content = content.replace(old_version, version)
        print(f"  ✅ Replaced all occurrences with {version}")
    
    # Update InstallerSha256 if provided
    if sha256:
        content = re.sub(
            r'InstallerSha256:\s*[A-Fa-f0-9]+',
            f'InstallerSha256: {sha256}',
            content
        )
        print(f"  ✅ Updated InstallerSha256")
    
    # Update SignatureSha256 if provided (for MSIX packages)
    if signature_sha256:
        content = re.sub(
            r'SignatureSha256:\s*[A-Fa-f0-9]+',
            f'SignatureSha256: {signature_sha256}',
            content
        )
        print(f"  ✅ Updated SignatureSha256")
    
    # Update ReleaseDate to today (ISO 8601 format: YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    content = re.sub(
        r'ReleaseDate:\s*[\d-]+',
        f'ReleaseDate: {today}',
        content
    )
    print(f"  ✅ Updated ReleaseDate to {today}")
    
    # Update ReleaseNotes if provided (for GitHub releases)
    if release_notes:
        # Escape special characters for YAML block scalar
        # Use |- for literal block scalar (strips trailing newlines)
        yaml_notes = release_notes.replace('\r\n', '\n').replace('\r', '\n')
        
        # Replace ReleaseNotes field (handles both single line and block scalar)
        if re.search(r'ReleaseNotes:\s*\|-', content):
            # Block scalar format - replace everything until next field
            content = re.sub(
                r'ReleaseNotes:\s*\|-\n(?:.*\n)*?(?=\w+:)',
                f'ReleaseNotes: |-\n  {yaml_notes.replace(chr(10), chr(10) + "  ")}\n',
                content,
                flags=re.MULTILINE
            )
            print(f"  ✅ Updated ReleaseNotes (block scalar)")
        else:
            # Single line or missing - add as block scalar
            content = re.sub(
                r'(ReleaseNotes:).*',
                f'ReleaseNotes: |-\n  {yaml_notes.replace(chr(10), chr(10) + "  ")}',
                content
            )
            print(f"  ✅ Updated ReleaseNotes")
    
    # Update ReleaseNotesUrl if provided
    if release_notes_url:
        content = re.sub(
            r'ReleaseNotesUrl:.*',
            f'ReleaseNotesUrl: {release_notes_url}',
            content
        )
        print(f"  ✅ Updated ReleaseNotesUrl")
    
    return content


def clone_winget_pkgs(fork_owner: str, temp_dir: str, token: str) -> bool:
    """Clone forked winget-pkgs repository and setup upstream"""
    try:
        # Use token in URL for authentication
        repo_url = f"https://{token}@github.com/{fork_owner}/winget-pkgs.git"
        print(f"Cloning https://github.com/{fork_owner}/winget-pkgs.git...")
        
        subprocess.run(
            ['git', 'clone', '--depth', '1', repo_url, temp_dir],
            check=True,
            capture_output=True
        )
        
        # Configure git
        subprocess.run(
            ['git', 'config', 'user.name', 'github-actions[bot]'],
            cwd=temp_dir,
            check=True
        )
        subprocess.run(
            ['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'],
            cwd=temp_dir,
            check=True
        )
        
        # Add upstream remote for microsoft/winget-pkgs
        print("Adding upstream remote (microsoft/winget-pkgs)...")
        subprocess.run(
            ['git', 'remote', 'add', 'upstream', 'https://github.com/microsoft/winget-pkgs.git'],
            cwd=temp_dir,
            check=True,
            capture_output=True
        )
        
        # Fetch main branch from upstream (shallow fetch)
        print("Fetching from upstream...")
        subprocess.run(
            ['git', 'fetch', 'upstream', 'main', '--depth=1'],
            cwd=temp_dir,
            check=True,
            capture_output=True
        )
        
        print("✅ Fork cloned with upstream remote configured")
        return True
    except Exception as e:
        print(f"Error cloning repository: {e}", file=sys.stderr)
        return False


def create_pr_branch(repo_dir: str, package_id: str, version: str) -> str:
    """Create and checkout new branch for PR from upstream/main"""
    branch_name = f"{package_id}-{version}"
    try:
        print(f"Creating branch '{branch_name}' from upstream/main...")
        subprocess.run(
            ['git', 'checkout', '-b', branch_name, 'upstream/main'],
            cwd=repo_dir,
            check=True,
            capture_output=True
        )
        print(f"✅ Branch created: {branch_name}")
        return branch_name
    except Exception as e:
        print(f"Error creating branch: {e}", file=sys.stderr)
        raise


def update_manifests(
    repo_dir: str,
    manifest_path: str,
    package_id: str,
    version: str,
    installer_url: str,
    release_notes: Optional[str] = None,
    release_notes_url: Optional[str] = None
) -> bool:
    """Update manifest files in the cloned repository"""
    try:
        # Determine file extension from URL
        file_ext = '.msix' if installer_url.lower().endswith('.msix') else '.exe'
        is_msix = file_ext == '.msix'
        
        # Download installer to calculate SHA256
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            tmp_path = tmp_file.name
        
        if not download_file(installer_url, tmp_path):
            return False
        
        sha256 = calculate_sha256(tmp_path)
        print(f"Calculated InstallerSha256: {sha256}")
        
        # Calculate SignatureSha256 for MSIX packages
        signature_sha256 = None
        if is_msix:
            print("MSIX package detected, calculating SignatureSha256...")
            signature_sha256 = calculate_msix_signature_sha256(tmp_path)
        
        os.unlink(tmp_path)
        
        # Update manifest files
        version_dir = os.path.join(repo_dir, manifest_path, version)
        
        # Check if version already exists
        if os.path.exists(version_dir):
            print(f"Version {version} already exists in repository")
            return False
        
        # Find latest version directory
        manifest_base = os.path.join(repo_dir, manifest_path)
        if not os.path.exists(manifest_base):
            print(f"Manifest path not found: {manifest_base}")
            return False
        
        versions = [d for d in os.listdir(manifest_base) if os.path.isdir(os.path.join(manifest_base, d))]
        if not versions:
            print("No existing versions found")
            return False
        
        # Sort versions and get latest
        versions.sort(key=lambda v: [int(x) for x in v.split('.')])
        latest_version = versions[-1]
        latest_dir = os.path.join(manifest_base, latest_version)
        
        print(f"Copying from latest version: {latest_version}")
        
        # Create new version directory
        os.makedirs(version_dir, exist_ok=True)
        
        # Copy and update each manifest file
        for filename in os.listdir(latest_dir):
            if filename.endswith('.yaml'):
                src_file = os.path.join(latest_dir, filename)
                dst_file = os.path.join(version_dir, filename)
                
                with open(src_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Determine if this is locale file (for ReleaseNotes)
                is_locale_file = '.locale.' in filename
                
                # Update content with hashes and optionally release notes
                if is_locale_file and release_notes:
                    # Update locale file with release notes
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256, 
                        release_notes, release_notes_url
                    )
                else:
                    # Update other files without release notes
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256
                    )
                
                with open(dst_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                print(f"Updated: {filename}")
        
        return True
        
    except Exception as e:
        print(f"Error updating manifests: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def commit_and_push(repo_dir: str, package_id: str, version: str, branch_name: str, token: str) -> bool:
    """Commit changes and push to fork"""
    try:
        # Add changes
        subprocess.run(
            ['git', 'add', '.'],
            cwd=repo_dir,
            check=True
        )
        
        # Commit
        commit_msg = f"New version: {package_id} version {version}"
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=repo_dir,
            check=True
        )
        
        # Get remote URL with token
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        remote_url = result.stdout.strip()
        
        # Update remote URL with token if not already present
        if token not in remote_url and not remote_url.startswith('https://'):
            # Assume it's SSH, convert to HTTPS with token
            if remote_url.startswith('git@github.com:'):
                repo_path = remote_url.replace('git@github.com:', '').replace('.git', '')
                remote_url = f"https://{token}@github.com/{repo_path}.git"
                subprocess.run(
                    ['git', 'remote', 'set-url', 'origin', remote_url],
                    cwd=repo_dir,
                    check=True
                )
        
        # Push
        subprocess.run(
            ['git', 'push', 'origin', branch_name],
            cwd=repo_dir,
            check=True
        )
        
        return True
    except Exception as e:
        print(f"Error committing/pushing: {e}", file=sys.stderr)
        return False


def create_pull_request(
    fork_owner: str,
    package_id: str,
    version: str,
    branch_name: str,
    workflow_run_number: str,
    workflow_run_id: str,
    repo_name: str = "winget-pkgs-updater"
) -> bool:
    """Create pull request using GitHub CLI"""
    try:
        title = f"New version: {package_id} version {version}"
        print(f"Creating PR: {title}")
        
        # Build PR body with separate links for repo and workflow run
        repo_url = f"https://github.com/{fork_owner}/{repo_name}"
        workflow_url = f"https://github.com/{fork_owner}/{repo_name}/actions/runs/{workflow_run_id}"
        body = f"Automated by [{fork_owner}/{repo_name}]({repo_url}) in workflow run [#{workflow_run_number}]({workflow_url})."
        
        # Use gh CLI to create PR
        subprocess.run(
            [
                'gh', 'pr', 'create',
                '--repo', 'microsoft/winget-pkgs',
                '--title', title,
                '--body', body,
                '--head', f"{fork_owner}:{branch_name}"
            ],
            check=True
        )
        
        print(f"✅ Pull request created: {title}")
        print(f"📝 Workflow run: {workflow_url}")
        return True
        
    except Exception as e:
        print(f"Error creating PR: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Update WinGet manifest with new version'
    )
    parser.add_argument('checkver_config', help='Path to checkver config file')
    parser.add_argument('version_info', help='Path to version info JSON file')
    parser.add_argument('--no-pr', action='store_true',
                        help='Update manifests without creating PR (for testing)')
    parser.add_argument('--fork-path', help='Path to existing fork clone (for testing)')
    
    args = parser.parse_args()
    
    # Load version info from check_version.py output
    with open(args.version_info, 'r') as f:
        version_info = json.load(f)
    
    package_id = version_info['packageIdentifier']
    version = version_info['version']
    installer_url = version_info['installerUrl']
    checkver_config = version_info['checkver_config']
    manifest_path = checkver_config.get('manifestPath', '')
    
    # Get release notes if available
    release_notes = version_info.get('releaseNotes')
    release_notes_url = version_info.get('releaseNotesUrl')
    
    print(f"Updating {package_id} to version {version}")
    
    if release_notes:
        print(f"📝 Release notes available ({len(release_notes)} chars)")
    
    # Check if PR already exists BEFORE doing any work (skip if --no-pr)
    if not args.no_pr and check_existing_pr(package_id, version):
        print("⏭️  Skipping update - PR already exists")
        sys.exit(0)  # Exit successfully - no work needed
    
    # Get environment variables
    fork_owner = os.getenv('GITHUB_REPOSITORY_OWNER', 'zeldrisho')
    workflow_run_number = os.getenv('GITHUB_RUN_NUMBER', 'unknown')
    workflow_run_id = os.getenv('GITHUB_RUN_ID', 'unknown')
    repo_name = os.getenv('GITHUB_REPOSITORY', 'zeldrisho/winget-pkgs-updater').split('/')[-1]
    token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    
    if not token:
        print("Error: GITHUB_TOKEN or GH_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Use provided fork path or create temporary directory
    if args.fork_path:
        # Use existing fork clone
        repo_dir = args.fork_path
        print(f"Using existing fork at: {repo_dir}")
        
        # Update manifests with release notes
        if not update_manifests(repo_dir, manifest_path, package_id, version, installer_url, release_notes, release_notes_url):
            print("Failed to update manifests")
            sys.exit(1)
        
        print(f"✅ Successfully updated manifests in {repo_dir}")
    else:
        # Create temporary directory for cloning (original workflow)
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = os.path.join(temp_dir, 'winget-pkgs')
            
            # Clone fork
            if not clone_winget_pkgs(fork_owner, repo_dir, token):
                print("Failed to clone repository")
                sys.exit(1)
            
            # Create branch
            branch_name = create_pr_branch(repo_dir, package_id, version)
            print(f"Created branch: {branch_name}")
            
            # Update manifests with release notes
            if not update_manifests(repo_dir, manifest_path, package_id, version, installer_url, release_notes, release_notes_url):
                print("Failed to update manifests")
                sys.exit(1)
            
            # Commit and push
            if not commit_and_push(repo_dir, package_id, version, branch_name, token):
                print("Failed to commit/push changes")
                sys.exit(1)
            
            # Create PR (skip if --no-pr)
            if not args.no_pr:
                if not create_pull_request(fork_owner, package_id, version, branch_name, workflow_run_number, workflow_run_id, repo_name):
                    print("Failed to create pull request")
                    sys.exit(1)
                
                print(f"✅ Successfully created PR for {package_id} version {version}")
            else:
                print(f"✅ Successfully updated manifests for {package_id} version {version} (no PR created)")


if __name__ == '__main__':
    main()
