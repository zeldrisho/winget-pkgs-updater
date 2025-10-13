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
from typing import Optional, Dict
from bs4 import BeautifulSoup


def load_manifest(manifest_path: str) -> Dict:
    """Load manifest configuration from YAML file"""
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


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


def get_installer_url(manifest: Dict, version: str) -> str:
    """Generate installer URL from pattern"""
    pattern = manifest.get('installerUrlPattern', '')
    return pattern.format(version=version)


def verify_installer_exists(url: str) -> bool:
    """Verify that the installer URL is accessible"""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except Exception as e:
        print(f"Error verifying installer URL {url}: {e}", file=sys.stderr)
        return False


def check_version(manifest_path: str) -> Optional[Dict]:
    """Check for new version and return update info if found"""
    manifest = load_manifest(manifest_path)
    package_id = manifest['packageIdentifier']
    check_url = manifest['checkUrl']
    
    print(f"Checking for updates: {package_id}")
    print(f"Check URL: {check_url}")
    
    # Get latest version
    latest_version = get_latest_version_from_web(check_url)
    if not latest_version:
        print("Could not determine latest version")
        return None
    
    print(f"Latest version found: {latest_version}")
    
    # Get installer URL
    installer_url = get_installer_url(manifest, latest_version)
    print(f"Installer URL: {installer_url}")
    
    # Verify installer exists
    if not verify_installer_exists(installer_url):
        print("Warning: Installer URL is not accessible")
        # Continue anyway - the URL might become accessible later
    
    return {
        'packageIdentifier': package_id,
        'version': latest_version,
        'installerUrl': installer_url,
        'manifest': manifest
    }


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: check_version.py <manifest.yaml>")
        sys.exit(1)
    
    manifest_path = sys.argv[1]
    if not os.path.exists(manifest_path):
        print(f"Manifest file not found: {manifest_path}")
        sys.exit(1)
    
    result = check_version(manifest_path)
    if result:
        # Output as JSON for GitHub Actions
        print("\n=== VERSION INFO ===")
        print(json.dumps(result, indent=2))
        
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
