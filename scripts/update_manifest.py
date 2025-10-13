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
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def check_existing_pr(package_id: str, version: str) -> bool:
    """
    Check if PR already exists for this package version.
    Returns True if PR exists (should skip), False if no PR found (should create).
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
                        state_emoji = "🟢" if pr['state'] == "OPEN" else "🟣" if pr['state'] == "MERGED" else "⚪"
                        print(f"⏭️  {state_emoji} PR already exists: #{pr['number']} ({pr['state']})")
                        print(f"   Title: {pr['title']}")
                        print(f"   URL: https://github.com/microsoft/winget-pkgs/pull/{pr['number']}")
                        return True  # Skip - PR exists
        
        print("✅ No existing PR found - will create new one")
        return False  # No PR found - should create
        
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


def update_manifest_content(content: str, version: str, sha256: Optional[str] = None) -> str:
    """
    Update version and SHA256 in manifest content.
    
    Strategy:
    1. Extract old version from PackageVersion field
    2. Replace ALL occurrences of old version with new version
    3. Update SHA256 if provided
    4. Update ReleaseDate to today
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
    
    # Update SHA256 if provided
    if sha256:
        content = re.sub(
            r'InstallerSha256:\s*[A-Fa-f0-9]+',
            f'InstallerSha256: {sha256}',
            content
        )
        print(f"  ✅ Updated SHA256")
    
    # Update ReleaseDate to today (ISO 8601 format: YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    content = re.sub(
        r'ReleaseDate:\s*[\d-]+',
        f'ReleaseDate: {today}',
        content
    )
    print(f"  ✅ Updated ReleaseDate to {today}")
    
    return content


def clone_winget_pkgs(fork_owner: str, temp_dir: str, token: str) -> bool:
    """Clone forked winget-pkgs repository"""
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
        
        return True
    except Exception as e:
        print(f"Error cloning repository: {e}", file=sys.stderr)
        return False


def create_pr_branch(repo_dir: str, package_id: str, version: str) -> str:
    """Create and checkout new branch for PR"""
    branch_name = f"{package_id}-{version}"
    try:
        subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=repo_dir,
            check=True,
            capture_output=True
        )
        return branch_name
    except Exception as e:
        print(f"Error creating branch: {e}", file=sys.stderr)
        raise


def update_manifests(
    repo_dir: str,
    manifest_path: str,
    package_id: str,
    version: str,
    installer_url: str
) -> bool:
    """Update manifest files in the cloned repository"""
    try:
        # Download installer to calculate SHA256
        with tempfile.NamedTemporaryFile(delete=False, suffix='.exe') as tmp_file:
            tmp_path = tmp_file.name
        
        if not download_file(installer_url, tmp_path):
            return False
        
        sha256 = calculate_sha256(tmp_path)
        print(f"Calculated SHA256: {sha256}")
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
                
                # Update content
                updated_content = update_manifest_content(content, version, sha256)
                
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
    if len(sys.argv) < 2:
        print("Usage: update_manifest.py <version_info.json>")
        sys.exit(1)
    
    # Load version info from check_version.py output
    version_info_file = sys.argv[1]
    with open(version_info_file, 'r') as f:
        version_info = json.load(f)
    
    package_id = version_info['packageIdentifier']
    version = version_info['version']
    installer_url = version_info['installerUrl']
    checkver_config = version_info['checkver_config']
    manifest_path = checkver_config.get('manifestPath', '')
    
    print(f"Updating {package_id} to version {version}")
    
    # Check if PR already exists BEFORE doing any work
    if check_existing_pr(package_id, version):
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
    
    # Create temporary directory for cloning
    with tempfile.TemporaryDirectory() as temp_dir:
        repo_dir = os.path.join(temp_dir, 'winget-pkgs')
        
        # Clone fork
        if not clone_winget_pkgs(fork_owner, repo_dir, token):
            print("Failed to clone repository")
            sys.exit(1)
        
        # Create branch
        branch_name = create_pr_branch(repo_dir, package_id, version)
        print(f"Created branch: {branch_name}")
        
        # Update manifests
        if not update_manifests(repo_dir, manifest_path, package_id, version, installer_url):
            print("Failed to update manifests")
            sys.exit(1)
        
        # Commit and push
        if not commit_and_push(repo_dir, package_id, version, branch_name, token):
            print("Failed to commit/push changes")
            sys.exit(1)
        
        # Create PR
        if not create_pull_request(fork_owner, package_id, version, branch_name, workflow_run_number, workflow_run_id, repo_name):
            print("Failed to create pull request")
            sys.exit(1)
    
    print(f"✅ Successfully created PR for {package_id} version {version}")


if __name__ == '__main__':
    main()
