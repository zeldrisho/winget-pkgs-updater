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


def get_latest_version_script(checkver_config: Dict) -> Optional[str]:
    """Extract version using PowerShell script method"""
    try:
        checkver = checkver_config.get('checkver', {})
        
        # Check if this uses script-based checkver
        if checkver.get('type') != 'script':
            return None
            
        script = checkver.get('script', '')
        regex_pattern = checkver.get('regex', '')
        
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
            version = match.group(1)
            print(f"Extracted version: {version}")
            return version
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


def get_installer_url(checkver_config: Dict, version: str) -> str:
    """Generate installer URL from template"""
    template = checkver_config.get('installerUrlTemplate', '')
    
    # Handle versionShort placeholder (e.g., 2.3.12.0 -> 2.3.12)
    version_short = re.sub(r'\.0$', '', version)
    
    return template.format(version=version, versionShort=version_short)


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
    
    # Try script-based checkver first
    latest_version = get_latest_version_script(checkver_config)
    
    # Fallback to web-based checkver if script method didn't work
    if not latest_version and 'checkUrl' in checkver_config:
        check_url = checkver_config['checkUrl']
        print(f"Falling back to web-based check URL: {check_url}")
        latest_version = get_latest_version_from_web(check_url)
    
    if not latest_version:
        print("Could not determine latest version")
        return None
    
    print(f"Latest version found: {latest_version}")
    
    # Get installer URL
    installer_url = get_installer_url(checkver_config, latest_version)
    print(f"Installer URL: {installer_url}")
    
    # Verify installer exists
    if not verify_installer_exists(installer_url):
        print("Warning: Installer URL is not accessible")
        # Continue anyway - the URL might become accessible later
    
    return {
        'packageIdentifier': package_id,
        'version': latest_version,
        'installerUrl': installer_url,
        'checkver_config': checkver_config
    }


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
