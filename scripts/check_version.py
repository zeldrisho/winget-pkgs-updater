#!/usr/bin/env python3
"""
Version checker for WinGet packages
Detects new versions by scraping download pages or APIs
"""

import os
import re
import sys
import json
import yaml
import requests
import subprocess
from typing import Optional, Dict
from bs4 import BeautifulSoup


def load_checkver_config(checkver_path: str) -> Dict:
    """Load checkver configuration from YAML file"""
    with open(checkver_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_powershell_script(script: str) -> Optional[str]:
    """Execute PowerShell script and return output"""
    try:
        # Run PowerShell script
        result = subprocess.run(
            ['pwsh', '-Command', script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception as e:
        print(f"Error running PowerShell script: {e}", file=sys.stderr)
        return None


def get_latest_version_github(checkver_config: Dict) -> Optional[tuple]:
    """
    Get latest version from GitHub releases.
    Returns tuple of (version, metadata_dict) where metadata can contain
    release notes and URL.
    
    Supports two config formats:
    1. checkver: { type: "github", repo: "owner/repo", ... }
    2. checkver: "github" with github: { owner: "...", repo: "..." }
    
    Handles version formatting:
    - If appendDotZero is true, appends .0 to 3-part versions (e.g., 7.5.4 -> 7.5.4.0)
    - Useful for packages that use 3-part versions in GitHub but 4-part in WinGet
    """
    try:
        checkver = checkver_config.get('checkver', {})
        
        # Support simple string format: checkver: "github"
        if checkver == 'github':
            github_config = checkver_config.get('github', {})
            owner = github_config.get('owner', '')
            repo = github_config.get('repo', '')
            if not owner or not repo:
                print("Missing 'owner' or 'repo' in github config")
                return None
            repo_full = f"{owner}/{repo}"
            regex_pattern = github_config.get('regex', 'v?([\\d\\.]+)')
            append_dot_zero = github_config.get('appendDotZero', False)
        # Support dict format: checkver: { type: "github", repo: "owner/repo" }
        elif isinstance(checkver, dict) and checkver.get('type') == 'github':
            repo_full = checkver.get('repo', '')
            if not repo_full:
                print("Missing 'repo' field in GitHub checkver config")
                return None
            regex_pattern = checkver.get('regex', 'v?([\\d\\.]+)')
            append_dot_zero = checkver.get('appendDotZero', False)
        else:
            return None
        
        # Fetch latest release from GitHub API
        api_url = f"https://api.github.com/repos/{repo_full}/releases/latest"
        print(f"Fetching latest release from: {api_url}")
        
        headers = {'User-Agent': 'winget-pkgs-updater'}
        # Add GitHub token if available to avoid rate limiting
        github_token = os.getenv('GITHUB_TOKEN') or os.getenv('WINGET_PKGS_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Error: GitHub API returned status {response.status_code}")
            return None
        
        release_data = response.json()
        tag_name = release_data.get('tag_name', '')
        
        # Extract version using regex (supports removing 'v' prefix)
        match = re.search(regex_pattern, tag_name)
        if match:
            version = match.group(1)
        else:
            # Fallback: remove 'v' prefix if present
            version = tag_name.lstrip('v')
        
        # Handle version formatting based on appendDotZero setting
        if append_dot_zero:
            # Check if version has exactly 3 parts (e.g., 7.5.4)
            version_parts = version.split('.')
            if len(version_parts) == 3:
                version = version + '.0'
                print(f"Appended .0 to version: {version}")
        
        print(f"Latest version found: {version}")
        
        # Build metadata dict
        metadata = {}
        
        # Check if updateMetadata is defined
        update_metadata = checkver_config.get('updateMetadata', [])
        
        # Add release notes if requested
        if 'ReleaseNotes' in update_metadata:
            release_notes = release_data.get('body', '').strip()
            if release_notes:
                metadata['releasenotes'] = release_notes
                print(f"✅ Fetched ReleaseNotes ({len(release_notes)} chars)")
            else:
                print(f"⚠️  ReleaseNotes requested but not available in GitHub release")
        
        # Add release notes URL if requested
        if 'ReleaseNotesUrl' in update_metadata:
            release_url = release_data.get('html_url', '')
            if release_url:
                metadata['releasenotesurl'] = release_url
                print(f"✅ Fetched ReleaseNotesUrl: {release_url}")
            else:
                print(f"⚠️  ReleaseNotesUrl requested but not available in GitHub release")
        
        return (version, metadata)
        
    except Exception as e:
        print(f"Error in GitHub-based version check: {e}", file=sys.stderr)
        return None


def get_latest_version_script(checkver_config: Dict) -> Optional[tuple]:
    r"""
    Extract version using PowerShell script method.
    Returns tuple of (version, metadata_dict) where metadata contains
    named groups from regex match for use in URL templates.
    
    Supports optional 'replace' field for transforming matched version string.
    Example: regex "(\d{2})/(\d{2})/(\d{4})" with replace "${3}.${1}.${2}"
    transforms "10/13/2025" to "2025.10.13"
    """
    try:
        checkver = checkver_config.get('checkver', {})
        
        # Check if this uses script-based checkver
        if checkver.get('type') != 'script':
            return None
            
        script = checkver.get('script', '')
        regex_pattern = checkver.get('regex', '')
        replace_pattern = checkver.get('replace', '')
        
        if not script or not regex_pattern:
            print("Missing script or regex in checkver config")
            return None
        
        # Run the PowerShell script
        output = run_powershell_script(script)
        if not output:
            print("PowerShell script returned no output")
            return None
        
        print(f"Script output: {output}")
        
        # Extract version using regex
        match = re.search(regex_pattern, output)
        if match:
            # If replace pattern is provided, use it to transform the version
            if replace_pattern:
                # Replace ${1}, ${2}, etc. with corresponding capture groups
                version = replace_pattern
                for i, group in enumerate(match.groups(), start=1):
                    version = version.replace(f"${{{i}}}", group)
                print(f"Applied replace pattern: {version}")
            else:
                # Default: use first capture group
                version = match.group(1)
            
            print(f"Extracted version: {version}")
            
            # Extract all named groups as metadata
            # This allows custom placeholders like {rcversion}, {build}, etc.
            metadata = match.groupdict()
            if metadata:
                print(f"Extracted metadata: {metadata}")
            
            return (version, metadata)
        else:
            print(f"Regex pattern '{regex_pattern}' did not match output")
            return None
            
    except Exception as e:
        print(f"Error in script-based version check: {e}", file=sys.stderr)
        return None


def get_latest_version_from_web(check_url: str) -> Optional[str]:
    """Extract version from web page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(check_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Look for version patterns in the HTML
        # Common patterns: v1.2.3, 1.2.3, version 1.2.3
        patterns = [
            r'Zalo-(\d+\.\d+\.\d+)-win64\.msi',
            r'version["\s:]+(\d+\.\d+\.\d+)',
            r'v(\d+\.\d+\.\d+)',
            r'(\d+\.\d+\.\d+)',
        ]
        
        content = response.text
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Return the first match that looks like a valid version
                version = matches[0]
                if re.match(r'^\d+\.\d+\.\d+$', version):
                    return version
        
        return None
    except Exception as e:
        print(f"Error fetching version from {check_url}: {e}", file=sys.stderr)
        return None


def get_installer_url(checkver_config: Dict, version: str, metadata: Dict = None) -> str:
    """
    Generate installer URL from template.
    Supports placeholders:
    - {version}: Full version (e.g., 4.6.250531)
    - {versionShort}: Version without trailing .0 (e.g., 4.6.250531 -> 4.6.250531, 2.4.4.0 -> 2.4.4)
    - Any named group from regex metadata (e.g., {rcversion}, {build})
    """
    template = checkver_config.get('installerUrlTemplate', '')
    
    if not metadata:
        metadata = {}
    
    # Handle versionShort placeholder (e.g., 2.3.12.0 -> 2.3.12)
    version_short = re.sub(r'\.0$', '', version)
    
    # Build replacement dict with version, versionShort, and all metadata
    replacements = {
        'version': version,
        'versionShort': version_short,
        **metadata  # Include all custom metadata (rcversion, build, etc.)
    }
    
    return template.format(**replacements)


def get_github_release_info(checkver_config: Dict, version: str) -> Optional[Dict]:
    """
    Fetch release notes and URL from GitHub API if this is a GitHub-based package.
    Returns dict with releaseNotes and releaseNotesUrl, or None if not GitHub or error.
    """
    try:
        # Check if this is a GitHub releases package
        checkver = checkver_config.get('checkver', {})
        script = checkver.get('script', '')
        
        # Look for GitHub API URL in the script
        github_api_match = re.search(r'github\.com/repos/([^/]+)/([^/]+)/releases', script)
        if not github_api_match:
            return None
        
        owner = github_api_match.group(1)
        repo = github_api_match.group(2)
        
        # Remove .0 suffix from version for GitHub tag (e.g., 2.4.4.0 -> 2.4.4)
        tag_version = re.sub(r'\.0$', '', version)
        tag_name = f"v{tag_version}"
        
        # Fetch release info from GitHub API
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag_name}"
        print(f"Fetching release info from: {api_url}")
        
        headers = {'User-Agent': 'winget-pkgs-updater'}
        # Add GitHub token if available to avoid rate limiting
        github_token = os.getenv('GITHUB_TOKEN') or os.getenv('WINGET_PKGS_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        response = requests.get(api_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            release_data = response.json()
            release_notes = release_data.get('body', '').strip()
            release_url = release_data.get('html_url', '')
            
            if release_notes:
                print(f"✅ Fetched release notes ({len(release_notes)} chars)")
                return {
                    'releaseNotes': release_notes,
                    'releaseNotesUrl': release_url
                }
        else:
            print(f"Warning: Could not fetch release info (status {response.status_code})")
            
    except Exception as e:
        print(f"Warning: Error fetching GitHub release info: {e}")
    
    return None


def get_release_info_from_config(checkver_config: Dict, metadata: Dict) -> Optional[Dict]:
    """
    Get release notes from checkver config or metadata if defined.
    Returns dict with releaseNotes and releaseNotesUrl, or None if not defined.
    """
    # First try to get from metadata (extracted from script output)
    release_notes = metadata.get('releasenotes') if metadata else None
    release_notes_url = metadata.get('releasenotesurl') if metadata else None
    
    # Fallback to checkver config
    if not release_notes:
        release_notes = checkver_config.get('releaseNotes')
    if not release_notes_url:
        release_notes_url = checkver_config.get('releaseNotesUrl')
    
    if not release_notes and not release_notes_url:
        return None
    
    # Format with metadata placeholders if needed
    if release_notes_url and metadata and '{' in release_notes_url:
        release_notes_url = release_notes_url.format(**metadata)
    
    result = {}
    if release_notes:
        result['releaseNotes'] = release_notes
    if release_notes_url:
        result['releaseNotesUrl'] = release_notes_url
    
    if result:
        print(f"✅ Release info: {result}")
    return result if result else None


def verify_installer_exists(url: str) -> bool:
    """Verify that the installer URL is accessible"""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except Exception as e:
        print(f"Error verifying installer URL {url}: {e}", file=sys.stderr)
        return False


def check_version(checkver_path: str) -> Optional[Dict]:
    """Check for new version and return update info if found"""
    checkver_config = load_checkver_config(checkver_path)
    package_id = checkver_config['packageIdentifier']
    
    print(f"Checking for updates: {package_id}")
    
    # Try GitHub-based checkver first
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
