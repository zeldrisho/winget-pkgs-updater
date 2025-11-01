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
import tempfile
import argparse
import subprocess
import requests
from pathlib import Path
from typing import Dict, List, Optional

# Import from modules
from git.pr import check_existing_pr, create_pull_request
from git.repo import clone_winget_pkgs, create_pr_branch, commit_and_push
from package.hasher import download_file, calculate_sha256
from package.msix import calculate_msix_signature_sha256
from package.msi import extract_product_code_from_msi
from yaml_utils import validate_yaml_content
from manifest.updater import update_manifest_content, add_missing_architectures
from version_utils import get_latest_version, compare_versions


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


def process_template_and_create_version(
    repo_dir: str,
    manifest_path: str,
    package_id: str,
    version: str,
    latest_dir: str,
    latest_version: str,
    sha256: Optional[str],
    signature_sha256: Optional[str],
    release_notes: Optional[str],
    release_notes_url: Optional[str],
    arch_hashes: Optional[Dict[str, str]],
    installer_urls: Optional[Dict[str, str]],
    installer_url: Optional[str],
    product_codes: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, str]] = None
) -> bool:
    """
    Copy and update manifest files from template to new version.
    This function is extracted to allow processing template from temporary directory.
    """
    try:
        version_dir = os.path.join(repo_dir, manifest_path, version)
        
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
                
                # Determine if this is installer or locale file
                is_locale_file = '.locale.' in filename
                is_installer_file = '.installer.' in filename
                
                # Update content with hashes and optionally release notes
                if is_locale_file and release_notes:
                    # Update locale file with release notes
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256, 
                        release_notes, release_notes_url, arch_hashes,
                        installer_urls, installer_url, product_codes, metadata,
                        package_id
                    )
                elif is_installer_file:
                    # Update installer file with multi-arch hashes and product codes
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256,
                        None, None, arch_hashes,
                        installer_urls, installer_url, product_codes, metadata,
                        package_id
                    )
                    # Add missing architectures (e.g., arm64 if not in old version)
                    if arch_hashes and installer_urls:
                        updated_content = add_missing_architectures(
                            updated_content, arch_hashes, installer_urls
                        )
                else:
                    # Update other files without release notes or multi-arch
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256,
                        None, None, arch_hashes,
                        installer_urls, installer_url, product_codes, metadata,
                        package_id
                    )
                
                with open(dst_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                # Validate YAML after writing
                print(f"Updated: {filename}")
                if not validate_yaml_content(updated_content, filename):
                    print(f"  ⚠️  Warning: {filename} may have validation issues")
        
        return True
        
    except Exception as e:
        print(f"Error processing template: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def update_manifests(
    repo_dir: str,
    manifest_path: str,
    package_id: str,
    version: str,
    installer_url: str,
    release_notes: Optional[str] = None,
    release_notes_url: Optional[str] = None,
    installer_urls: Optional[Dict[str, str]] = None,
    metadata: Optional[Dict[str, str]] = None
) -> bool:
    """Update manifest files in the cloned repository"""
    try:
        # Multi-architecture support
        if installer_urls:
            print(f"Multi-architecture package detected: {', '.join(installer_urls.keys())}")
            arch_hashes = {}
            product_codes = {}
            
            # Calculate hash for each architecture
            for arch, url in installer_urls.items():
                print(f"\n📥 Processing {arch} architecture...")
                # Determine file extension
                if url.lower().endswith('.msi'):
                    file_ext = '.msi'
                    is_msi = True
                elif url.lower().endswith('.msix'):
                    file_ext = '.msix'
                    is_msi = False
                elif url.lower().endswith('.zip'):
                    file_ext = '.zip'
                    is_msi = False
                else:
                    file_ext = '.exe'
                    is_msi = False
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    if not download_file(url, tmp_path):
                        print(f"❌ Failed to download {arch} installer")
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                        continue
                    
                    # Calculate SHA256
                    arch_hash = calculate_sha256(tmp_path)
                    arch_hashes[arch] = arch_hash
                    print(f"  ✅ {arch} SHA256: {arch_hash}")
                    
                    # Extract ProductCode from MSI files
                    if is_msi:
                        product_code = extract_product_code_from_msi(tmp_path)
                        if product_code:
                            product_codes[arch] = product_code
                
                except Exception as e:
                    print(f"❌ Error processing {arch} installer: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # Always cleanup temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            
            if not arch_hashes:
                print("Failed to calculate hashes for any architecture")
                return False
            
            # Use first architecture as primary for backward compatibility
            sha256 = list(arch_hashes.values())[0]
            signature_sha256 = None
        else:
            # Single architecture (legacy)
            # Determine file extension from URL
            if installer_url.lower().endswith('.msi'):
                file_ext = '.msi'
                is_msi = True
                is_msix = False
            elif installer_url.lower().endswith('.msix'):
                file_ext = '.msix'
                is_msi = False
                is_msix = True
            else:
                file_ext = '.exe'
                is_msi = False
                is_msix = False
            
            # Download installer to calculate SHA256
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                if not download_file(installer_url, tmp_path):
                    print("❌ Failed to download installer")
                    return False
                
                sha256 = calculate_sha256(tmp_path)
                print(f"✅ Calculated InstallerSha256: {sha256}")
                
                # Calculate SignatureSha256 for MSIX packages
                signature_sha256 = None
                if is_msix:
                    print("MSIX package detected, calculating SignatureSha256...")
                    signature_sha256 = calculate_msix_signature_sha256(tmp_path)
                
                # Extract ProductCode from MSI files
                product_codes = None
                if is_msi:
                    product_code = extract_product_code_from_msi(tmp_path)
                    if product_code:
                        product_codes = {'default': product_code}
                
            except Exception as e:
                print(f"❌ Error processing installer: {e}")
                import traceback
                traceback.print_exc()
                return False
            finally:
                # Always cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
            arch_hashes = None
        
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
            # Try to use template from specific commit if available
            config_file = None
            for f in ['manifests/*.checkver.yaml', 'manifests/**/*.checkver.yaml']:
                import glob
                matches = glob.glob(f)
                for match in matches:
                    with open(match, 'r') as cf:
                        checkver = yaml.safe_load(cf)
                        if checkver.get('packageIdentifier') == package_id:
                            config_file = match
                            break
                if config_file:
                    break
            
            if config_file:
                with open(config_file, 'r') as f:
                    checkver_config = yaml.safe_load(f)
                
                template_commit = checkver_config.get('templateCommit')
                template_version = checkver_config.get('templateVersion')
                
                if template_commit and template_version:
                    print(f"No existing versions found on master branch")
                    print(f"Using template version {template_version} from commit {template_commit}")
                    
                    # Fetch manifest from specific commit to TEMPORARY directory (outside repo)
                    # This ensures template files are NOT committed to Git
                    with tempfile.TemporaryDirectory() as temp_template_dir:
                        template_dir = os.path.join(temp_template_dir, template_version)
                        os.makedirs(template_dir, exist_ok=True)
                        
                        # Fetch all yaml files from the template commit
                        api_url = f"https://api.github.com/repos/microsoft/winget-pkgs/contents/{manifest_path}/{template_version}?ref={template_commit}"
                        try:
                            response = requests.get(api_url, timeout=30)
                            response.raise_for_status()
                            files = response.json()
                            
                            for file_info in files:
                                if file_info['name'].endswith('.yaml'):
                                    file_content = fetch_github_file(
                                        'microsoft/winget-pkgs',
                                        f"{manifest_path}/{template_version}/{file_info['name']}",
                                        template_commit
                                    )
                                    if file_content:
                                        with open(os.path.join(template_dir, file_info['name']), 'w', encoding='utf-8') as f:
                                            f.write(file_content)
                                        print(f"  Downloaded template: {file_info['name']}")
                            
                            versions = [template_version]
                            latest_version = template_version
                            latest_dir = template_dir
                            print(f"✅ Template version {template_version} fetched successfully")
                            print(f"   (Template stored in temporary directory, will not be committed)")
                            
                            # Process the template immediately within this context
                            # so latest_dir remains valid
                            return process_template_and_create_version(
                                repo_dir, manifest_path, package_id, version, latest_dir, latest_version,
                                sha256, signature_sha256, release_notes, release_notes_url,
                                arch_hashes, installer_urls, installer_url, product_codes, metadata
                            )
                        except Exception as e:
                            print(f"Error fetching template from commit {template_commit}: {e}")
                            return False
                else:
                    print("No existing versions found")
                    return False
            else:
                print("No existing versions found")
                return False
        else:
            # Sort versions and get latest using robust semantic version comparison
            latest_version = get_latest_version(versions)
            latest_dir = os.path.join(manifest_base, latest_version)
            
            print(f"Available versions in repository: {', '.join(versions[-5:]) if len(versions) >= 5 else ', '.join(versions)}")  # Show last 5 or all
            print(f"Selected latest version: {latest_version}")
            
            # Sanity check: warn if selected version is newer than or equal to target version
            if compare_versions(latest_version, version) >= 0:
                print(f"⚠️  WARNING: Latest version {latest_version} >= target version {version}")
                print(f"   This might indicate the version already exists or there's a versioning issue")
            
            # Process template from repo directory (normal case)
            return process_template_and_create_version(
                repo_dir, manifest_path, package_id, version, latest_dir, latest_version,
                sha256, signature_sha256, release_notes, release_notes_url,
                arch_hashes, installer_urls, installer_url, product_codes, metadata
            )
        
    except Exception as e:
        print(f"Error updating manifests: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Update WinGet manifest with new version'
    )
    parser.add_argument('checkver_config', help='Path to checkver config file')
    parser.add_argument('version_info', nargs='?', help='Path to version info JSON file OR package identifier (if version provided)')
    parser.add_argument('version', nargs='?', help='Version number (if package identifier provided as second arg)')
    parser.add_argument('--no-pr', action='store_true',
                        help='Update manifests without creating PR (for testing)')
    parser.add_argument('--fork-path', help='Path to existing fork clone (for testing)')
    
    args = parser.parse_args()
    
    # Determine if using direct args or JSON file
    if args.version:
        # Direct arguments mode: checkver_config package_id version
        package_id = args.version_info
        version = args.version
        
        # Load checkver config to get installer URLs
        print(f"Loading checkver config from: {args.checkver_config}")
        with open(args.checkver_config, 'r') as f:
            checkver_config = yaml.safe_load(f)
        
        # Get installer URL template
        installer_url_template = checkver_config.get('installerUrlTemplate')
        if not installer_url_template:
            print("Error: installerUrlTemplate not found in checkver config", file=sys.stderr)
            sys.exit(1)
        
        # Generate installer URLs
        version_short = version.rstrip('.0')
        if isinstance(installer_url_template, dict):
            # Multi-architecture
            installer_urls = {}
            for arch, url_template in installer_url_template.items():
                installer_urls[arch] = url_template.replace('{version}', version).replace('{versionShort}', version_short)
            installer_url = list(installer_urls.values())[0]  # Use first URL as primary
        else:
            # Single architecture
            installer_url = installer_url_template.replace('{version}', version).replace('{versionShort}', version_short)
            installer_urls = None
        
        # Get metadata - for GitHub releases, fetch release notes
        release_notes = None
        release_notes_url = None
        metadata = None
        
        checkver = checkver_config.get('checkver', {})
        if isinstance(checkver, dict) and checkver.get('type') == 'github':
            repo = checkver.get('repo')
            if repo:
                print(f"Fetching GitHub release metadata for {repo}...")
                # Fetch release info for this specific version
                from version.github import get_github_release_info
                # Build a temporary config that get_github_release_info can use
                temp_config = {'checkver': {'script': f'https://api.github.com/repos/{repo}/releases'}}
                release_info = get_github_release_info(temp_config, version)
                if release_info:
                    release_notes = release_info.get('releaseNotes')
                    release_notes_url = release_info.get('releaseNotesUrl')
        
        manifest_path = checkver_config.get('manifestPath', '')
        
    else:
        # JSON file mode (backward compatibility)
        # Load version info from check_version.py output
        with open(args.version_info, 'r') as f:
            version_info = json.load(f)
        
        package_id = version_info['packageIdentifier']
        version = version_info['version']
        installer_url = version_info['installerUrl']
        checkver_config = version_info['checkver_config']
        manifest_path = checkver_config.get('manifestPath', '')
        
        # Get multi-architecture URLs if available
        installer_urls = version_info.get('installerUrls')
        
        # Get release notes if available
        release_notes = version_info.get('releaseNotes')
        release_notes_url = version_info.get('releaseNotesUrl')
        
        # Get metadata for custom field updates (e.g., DisplayVersion)
        metadata = version_info.get('metadata')
    
    print(f"Updating {package_id} to version {version}")
    
    if installer_urls:
        print(f"Multi-architecture package: {', '.join(installer_urls.keys())}")
    
    if release_notes:
        print(f"📝 Release notes available ({len(release_notes)} chars)")
    
    if metadata and 'displayDate' in metadata:
        print(f"📅 Display date: {metadata['displayDate']}")
    
    # Get environment variables
    fork_repo = os.getenv('WINGET_FORK_REPO')
    if not fork_repo:
        fork_owner = os.getenv('GITHUB_REPOSITORY_OWNER', 'zeldrisho')
        fork_repo = f"{fork_owner}/winget-pkgs"
    
    workflow_run_number = os.getenv('GITHUB_RUN_NUMBER', 'unknown')
    workflow_run_id = os.getenv('GITHUB_RUN_ID', 'unknown')
    repo_name = os.getenv('GITHUB_REPOSITORY', 'zeldrisho/winget-pkgs-updater').split('/')[-1]
    token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    
    if not token:
        print("Error: GITHUB_TOKEN or GH_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Extract fork_owner from fork_repo for PR creation
    fork_owner = fork_repo.split('/')[0]
    
    # Use provided fork path or create temporary directory
    if args.fork_path:
        # Use existing fork clone
        repo_dir = args.fork_path
        print(f"Using existing fork at: {repo_dir}")
        
        # Update manifests with release notes and multi-arch support
        if not update_manifests(repo_dir, manifest_path, package_id, version, installer_url, release_notes, release_notes_url, installer_urls, metadata):
            print("Failed to update manifests")
            sys.exit(1)
        
        print(f"✅ Successfully updated manifests in {repo_dir}")
    else:
        # Create temporary directory for cloning (original workflow)
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = os.path.join(temp_dir, 'winget-pkgs')
            
            # Clone fork
            if not clone_winget_pkgs(fork_repo, repo_dir, token):
                print("Failed to clone repository")
                sys.exit(1)
            
            # Create branch
            branch_name = create_pr_branch(repo_dir, package_id, version)
            print(f"Created branch: {branch_name}")
            
            # Update manifests with release notes and multi-arch support
            if not update_manifests(repo_dir, manifest_path, package_id, version, installer_url, release_notes, release_notes_url, installer_urls, metadata):
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
