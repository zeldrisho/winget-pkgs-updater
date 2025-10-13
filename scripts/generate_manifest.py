#!/usr/bin/env python3
"""
Generate WinGet manifest files following microsoft/winget-pkgs format
Reference: https://github.com/microsoft/winget-pkgs
"""

import os
import sys
import json
import yaml
import hashlib
import requests
from typing import Dict, Optional


def download_and_hash(url: str) -> Optional[str]:
    """Download installer and compute SHA256 hash"""
    try:
        print(f"Downloading installer from {url}...")
        response = requests.get(url, timeout=300, stream=True)
        response.raise_for_status()
        
        sha256_hash = hashlib.sha256()
        total_size = 0
        
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                sha256_hash.update(chunk)
                total_size += len(chunk)
        
        print(f"Downloaded {total_size} bytes")
        return sha256_hash.hexdigest().upper()
    except Exception as e:
        print(f"Error downloading installer: {e}", file=sys.stderr)
        return None


def generate_version_manifest(config: Dict, version: str, installer_url: str, sha256: str) -> str:
    """Generate the version manifest (PackageIdentifier.PackageVersion.yaml)"""
    package_id = config['packageIdentifier']
    
    manifest = {
        'PackageIdentifier': package_id,
        'PackageVersion': version,
        'DefaultLocale': 'en-US',
        'ManifestType': 'version',
        'ManifestVersion': '1.6.0'
    }
    
    return yaml.dump(manifest, sort_keys=False, allow_unicode=True)


def generate_installer_manifest(config: Dict, version: str, installer_url: str, sha256: str) -> str:
    """Generate the installer manifest (PackageIdentifier.installer.yaml)"""
    package_id = config['packageIdentifier']
    
    manifest = {
        'PackageIdentifier': package_id,
        'PackageVersion': version,
        'Installers': [
            {
                'Architecture': config.get('architecture', 'x64'),
                'InstallerType': config.get('installerType', 'msi'),
                'InstallerUrl': installer_url,
                'InstallerSha256': sha256,
                'ProductCode': config.get('productCode', '{PRODUCTCODE}'),
                'Scope': 'machine'
            }
        ],
        'ManifestType': 'installer',
        'ManifestVersion': '1.6.0'
    }
    
    return yaml.dump(manifest, sort_keys=False, allow_unicode=True)


def generate_locale_manifest(config: Dict, version: str) -> str:
    """Generate the locale manifest (PackageIdentifier.locale.en-US.yaml)"""
    package_id = config['packageIdentifier']
    
    manifest = {
        'PackageIdentifier': package_id,
        'PackageVersion': version,
        'PackageLocale': 'en-US',
        'Publisher': config.get('publisher', 'Unknown'),
        'PackageName': config.get('packageName', package_id.split('.')[-1]),
        'License': config.get('license', 'Proprietary'),
        'ShortDescription': config.get('shortDescription', ''),
        'ManifestType': 'defaultLocale',
        'ManifestVersion': '1.6.0'
    }
    
    # Add optional fields
    if 'description' in config:
        manifest['Description'] = config['description']
    if 'releaseNotesUrl' in config:
        manifest['ReleaseNotesUrl'] = config['releaseNotesUrl']
    if 'tags' in config:
        manifest['Tags'] = config['tags']
    
    return yaml.dump(manifest, sort_keys=False, allow_unicode=True)


def create_manifests(config: Dict, version: str, installer_url: str, output_dir: str) -> bool:
    """Create all manifest files in the output directory"""
    package_id = config['packageIdentifier']
    
    # Download and hash installer
    print("Computing installer SHA256 hash...")
    sha256 = download_and_hash(installer_url)
    if not sha256:
        print("Failed to compute hash")
        return False
    
    print(f"SHA256: {sha256}")
    
    # Create output directory structure
    # Format: manifests/p/Publisher/PackageName/Version/
    parts = package_id.split('.')
    manifest_path = os.path.join(output_dir, parts[0][0].lower(), parts[0], parts[1], version)
    os.makedirs(manifest_path, exist_ok=True)
    
    # Generate manifest files
    print(f"Generating manifests in {manifest_path}")
    
    # Version manifest
    version_file = os.path.join(manifest_path, f"{package_id}.yaml")
    with open(version_file, 'w', encoding='utf-8') as f:
        f.write(generate_version_manifest(config, version, installer_url, sha256))
    print(f"Created: {version_file}")
    
    # Installer manifest
    installer_file = os.path.join(manifest_path, f"{package_id}.installer.yaml")
    with open(installer_file, 'w', encoding='utf-8') as f:
        f.write(generate_installer_manifest(config, version, installer_url, sha256))
    print(f"Created: {installer_file}")
    
    # Locale manifest
    locale_file = os.path.join(manifest_path, f"{package_id}.locale.en-US.yaml")
    with open(locale_file, 'w', encoding='utf-8') as f:
        f.write(generate_locale_manifest(config, version))
    print(f"Created: {locale_file}")
    
    return True


def main():
    """Main entry point"""
    if len(sys.argv) < 4:
        print("Usage: generate_manifest.py <config.yaml> <version> <installer_url> [output_dir]")
        sys.exit(1)
    
    config_path = sys.argv[1]
    version = sys.argv[2]
    installer_url = sys.argv[3]
    output_dir = sys.argv[4] if len(sys.argv) > 4 else '/tmp/winget-manifests'
    
    # Load config
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Create manifests
    success = create_manifests(config, version, installer_url, output_dir)
    
    if success:
        print("\n✓ Manifests generated successfully")
        # Set GitHub Actions output
        if os.getenv('GITHUB_OUTPUT'):
            with open(os.getenv('GITHUB_OUTPUT'), 'a') as f:
                package_id = config['packageIdentifier']
                parts = package_id.split('.')
                manifest_path = os.path.join(output_dir, parts[0][0].lower(), parts[0], parts[1], version)
                f.write(f"manifest_path={manifest_path}\n")
    else:
        print("\n✗ Failed to generate manifests")
        sys.exit(1)


if __name__ == '__main__':
    main()
