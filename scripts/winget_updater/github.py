"""
GitHub API integration for fetching release information
"""

import os
import re
import requests
from typing import Optional, Dict, Tuple


def get_latest_version_github(checkver_config: Dict) -> Optional[Tuple[str, Dict]]:
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
            append_dot_zero = github_config.get('appendDotZero', False)
        # Support dict format: checkver: { type: "github", repo: "owner/repo" }
        elif isinstance(checkver, dict) and checkver.get('type') == 'github':
            repo_full = checkver.get('repo', '')
            if not repo_full:
                print("Missing 'repo' field in GitHub checkver config")
                return None
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
        
        # Extract version - remove 'v' prefix if present
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
        print(f"Error in GitHub-based version check: {e}")
        return None


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
