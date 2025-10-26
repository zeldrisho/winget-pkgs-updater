#!/usr/bin/env python3
"""
Version checker for WinGet packages
Detects new versions by scraping download pages or APIs
"""

import os
import sys
import json
import subprocess
from typing import Optional, Dict

# Import modules
from config import load_checkver_config
from version.github import get_latest_version_github, get_github_release_info
from version.script import get_latest_version_script
from version.url import get_installer_url, verify_installer_exists, get_release_info_from_config
from version.web import get_latest_version_from_web
from version_utils import get_latest_version


def get_latest_version_in_winget_pkgs(manifest_path: str) -> Optional[str]:
    """
    Get the latest version available in microsoft/winget-pkgs.
    Returns None if manifest doesn't exist.
    """
    try:
        # Use gh api to list directory contents
        result = subprocess.run(
            ['gh', 'api', f'/repos/microsoft/winget-pkgs/contents/{manifest_path}'],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            # Manifest path doesn't exist
            return None
        
        import json
        contents = json.loads(result.stdout)
        
        # Filter for directories only (version folders)
        versions = [item['name'] for item in contents if item['type'] == 'dir']
        
        if not versions:
            return None
        
        # Use robust version sorting from version_utils
        return get_latest_version(versions)
        
    except Exception as e:
        print(f"Warning: Could not check microsoft/winget-pkgs: {e}", file=sys.stderr)
        return None


def check_version(checkver_path: str) -> Optional[Dict]:
    """Check for new version and return update info if found"""
    checkver_config = load_checkver_config(checkver_path)
    package_id = checkver_config['packageIdentifier']
    manifest_path = checkver_config.get('manifestPath', '')
    
    print(f"Checking for updates: {package_id}")
    
    # STEP 1: Check latest version on microsoft/winget-pkgs
    print(f"🔍 Checking latest version in microsoft/winget-pkgs...")
    winget_latest_version = get_latest_version_in_winget_pkgs(manifest_path)
    if winget_latest_version:
        print(f"   Latest in microsoft/winget-pkgs: {winget_latest_version}")
    else:
        print(f"   No existing version found in microsoft/winget-pkgs")
    
    # STEP 2: Try GitHub-based checkver first
    version_result = get_latest_version_github(checkver_config)
    metadata = {}
    
    # If not GitHub, try script-based checkver
    if not version_result:
        version_result = get_latest_version_script(checkver_config)
    
    if version_result:
        # Methods return (version, metadata) tuple
        if isinstance(version_result, tuple):
            latest_version, metadata = version_result
        else:
            # Fallback for old behavior
            latest_version = version_result
    else:
        latest_version = None
    
    # Fallback to web-based checkver if other methods didn't work
    if not latest_version and 'checkUrl' in checkver_config:
        check_url = checkver_config['checkUrl']
        print(f"Falling back to web-based check URL: {check_url}")
        latest_version = get_latest_version_from_web(check_url)
    
    if not latest_version:
        print("Could not determine latest version")
        return None
    
    print(f"Latest version found: {latest_version}")
    
    # STEP 3: Compare versions - skip if same
    if winget_latest_version and winget_latest_version == latest_version:
        print(f"✅ Version {latest_version} already exists in microsoft/winget-pkgs")
        print(f"⏭️  No update needed, skipping")
        return None
    
    # Get installer URL(s)
    # Check if installerUrlTemplate is dict (per-architecture) or string (single)
    installer_url_template = checkver_config.get('installerUrlTemplate', '')
    
    if isinstance(installer_url_template, dict):
        # Multi-architecture support
        print("Detected multi-architecture URL templates")
        installer_urls = {}
        for arch, template in installer_url_template.items():
            # Temporarily set template for this architecture
            temp_config = checkver_config.copy()
            temp_config['installerUrlTemplate'] = template
            url = get_installer_url(temp_config, latest_version, metadata)
            installer_urls[arch] = url
            print(f"  {arch}: {url}")
        
        # Use x64 as primary for backward compatibility
        installer_url = installer_urls.get('x64', list(installer_urls.values())[0])
    else:
        # Single architecture (traditional)
        installer_url = get_installer_url(checkver_config, latest_version, metadata)
        installer_urls = None
        print(f"Installer URL: {installer_url}")
    
    # Get GitHub release info if available
    release_info = get_github_release_info(checkver_config, latest_version)
    
    # If no GitHub release info, try to get from config
    if not release_info:
        release_info = get_release_info_from_config(checkver_config, metadata)
    
    # Verify installer exists (check primary URL only for multi-arch)
    if not verify_installer_exists(installer_url):
        print("Warning: Installer URL is not accessible")
        # Continue anyway - the URL might become accessible later
    
    result = {
        'packageIdentifier': package_id,
        'version': latest_version,
        'installerUrl': installer_url,  # Primary URL for backward compatibility
        'checkver_config': checkver_config
    }
    
    # Add multi-architecture URLs if available
    if installer_urls:
        result['installerUrls'] = installer_urls
    
    # Add metadata for custom placeholders if available
    if metadata:
        result['metadata'] = metadata
    
    # Add release info if available
    if release_info:
        result['releaseNotes'] = release_info['releaseNotes']
        result['releaseNotesUrl'] = release_info['releaseNotesUrl']
    
    return result


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: check_version.py <checkver.yaml> [output.json]")
        sys.exit(1)
    
    checkver_path = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    if not os.path.exists(checkver_path):
        print(f"Checkver file not found: {checkver_path}")
        sys.exit(1)
    
    result = check_version(checkver_path)
    if result:
        # Output as JSON for GitHub Actions
        print("\n=== VERSION INFO ===")
        print(json.dumps(result, indent=2))
        
        # Save to output file if specified
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nSaved to: {output_file}")
        
        # Set GitHub Actions output
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
                f.write(f"has_update=true\n")
                f.write(f"version={result['version']}\n")
                f.write(f"package_id={result['packageIdentifier']}\n")
                f.write(f"installer_url={result['installerUrl']}\n")
    else:
        print("No update found or error occurred")
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
                f.write(f"has_update=false\n")
        sys.exit(0)


if __name__ == '__main__':
    main()
