#!/usr/bin/env python3
"""
Create complete UniKey manifests with arm64 support
- Fetches raw manifests from microsoft/winget-pkgs
- Calculates correct SHA256 for each architecture
- Updates release notes from checkver
"""

import hashlib
import requests
import tempfile
import json
import subprocess
from pathlib import Path
from datetime import datetime


def download_and_hash(url: str) -> str:
    """Download file and calculate SHA256"""
    print(f"📥 Downloading: {url}")
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)
        
        tmp.flush()
        
        # Calculate hash
        sha256_hash = hashlib.sha256()
        with open(tmp.name, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        hash_value = sha256_hash.hexdigest().upper()
        print(f"✅ SHA256: {hash_value}")
        
        Path(tmp.name).unlink()
        return hash_value


def main():
    """Main entry point"""
    print("🚀 UniKey.UniKey - Creating complete manifests with arm64\n")
    
    # Get version info from checkver
    print("🔍 Running checkver to get latest version info...")
    result = subprocess.run(
        ['python3', 'scripts/check_version.py', 'manifests/UniKey.UniKey.checkver.yaml', '/tmp/unikey_version.json'],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Checkver failed: {result.stderr}")
        return
    
    # Load version info
    with open('/tmp/unikey_version.json', 'r') as f:
        version_info = json.load(f)
    
    version = version_info['version']
    urls = version_info['installerUrls']
    release_notes = version_info.get('releaseNotes', '')
    release_notes_url = version_info.get('releaseNotesUrl', '')
    
    print(f"✅ Version: {version}")
    print(f"✅ Release Notes: {release_notes}")
    print(f"✅ Release Notes URL: {release_notes_url}\n")
    
    # Calculate hashes for all architectures
    print("🔐 Calculating SHA256 hashes...\n")
    hashes = {}
    for arch, url in urls.items():
        try:
            hashes[arch] = download_and_hash(url)
            print()
        except Exception as e:
            print(f"❌ Error processing {arch}: {e}\n")
    
    if len(hashes) != 3:
        print("❌ Failed to calculate all hashes")
        return
    
    print("=" * 60)
    print("📋 HASH SUMMARY:")
    print("=" * 60)
    for arch, hash_value in hashes.items():
        print(f"{arch:6s}: {hash_value}")
    print("=" * 60)
    print()
    
    # Fetch raw manifests from microsoft/winget-pkgs
    latest_version = "4.6.230919"
    base_url = f"https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/u/UniKey/UniKey/{latest_version}"
    
    # 1. Installer manifest
    print("📡 Fetching installer manifest...")
    response = requests.get(f"{base_url}/UniKey.UniKey.installer.yaml", timeout=30)
    response.raise_for_status()
    installer_content = response.text
    print("✅ Fetched\n")
    
    print("📝 Updating installer manifest...\n")
    installer_lines = []
    current_arch = None
    today = datetime.now().strftime('%Y-%m-%d')
    
    for line in installer_content.split('\n'):
        # Skip old ManifestType and ManifestVersion
        if line.strip().startswith('ManifestType:') or line.strip().startswith('ManifestVersion:'):
            continue
        
        # Update version
        if 'PackageVersion:' in line:
            line = f'PackageVersion: {version}'
            print(f"✅ Updated PackageVersion to {version}")
        
        # Update ReleaseDate
        if 'ReleaseDate:' in line:
            line = f'ReleaseDate: {today}'
            print(f"✅ Updated ReleaseDate to {today}")
        
        # Track architecture
        if line.strip().startswith('- Architecture:'):
            current_arch = line.split(':')[1].strip()
        
        # Update URL
        if 'InstallerUrl:' in line and current_arch and current_arch in urls:
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f'InstallerUrl: {urls[current_arch]}'
            print(f"✅ Updated {current_arch} URL")
        
        # Update hash
        if 'InstallerSha256:' in line and current_arch and current_arch in hashes:
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f'InstallerSha256: {hashes[current_arch]}'
            print(f"✅ Updated {current_arch} hash")
        
        installer_lines.append(line)
    
    # Add arm64 if not exists
    if 'arm64' not in installer_content.lower():
        print("\n➕ Adding arm64 architecture...")
        arm64_section = [
            '- Architecture: arm64',
            '  NestedInstallerType: portable',
            '  NestedInstallerFiles:',
            '  - RelativeFilePath: UnikeyNT.exe',
            '    PortableCommandAlias: UnikeyNT',
            f'  InstallerUrl: {urls["arm64"]}',
            f'  InstallerSha256: {hashes["arm64"]}'
        ]
        installer_lines.extend(arm64_section)
        print("✅ Added arm64")
    
    # Add manifest metadata
    installer_lines.extend(['ManifestType: installer', 'ManifestVersion: 1.9.0'])
    
    # Save installer manifest
    with open('UniKey.UniKey.installer.yaml', 'w', encoding='utf-8') as f:
        f.write('\n'.join(installer_lines))
    print(f"\n✅ Saved: UniKey.UniKey.installer.yaml")
    
    # 2. Locale manifest
    print("\n📡 Fetching locale manifest...")
    response = requests.get(f"{base_url}/UniKey.UniKey.locale.en-US.yaml", timeout=30)
    response.raise_for_status()
    locale_content = response.text
    print("✅ Fetched\n")
    
    print("📝 Updating locale manifest...\n")
    locale_lines = []
    
    for line in locale_content.split('\n'):
        # Skip old metadata
        if line.strip().startswith('ManifestType:') or line.strip().startswith('ManifestVersion:'):
            continue
        
        # Update version
        if 'PackageVersion:' in line:
            line = f'PackageVersion: {version}'
        
        # Update ReleaseNotes
        if line.strip().startswith('ReleaseNotes:'):
            line = f'ReleaseNotes: {release_notes}'
            print(f"✅ Updated ReleaseNotes")
        
        # Update ReleaseNotesUrl
        if line.strip().startswith('ReleaseNotesUrl:'):
            line = f'ReleaseNotesUrl: {release_notes_url}'
            print(f"✅ Updated ReleaseNotesUrl")
        
        locale_lines.append(line)
    
    # Add manifest metadata
    locale_lines.extend(['ManifestType: defaultLocale', 'ManifestVersion: 1.9.0'])
    
    # Save locale manifest
    with open('UniKey.UniKey.locale.en-US.yaml', 'w', encoding='utf-8') as f:
        f.write('\n'.join(locale_lines))
    print(f"\n✅ Saved: UniKey.UniKey.locale.en-US.yaml")
    
    # 3. Version manifest
    print("\n📡 Fetching version manifest...")
    response = requests.get(f"{base_url}/UniKey.UniKey.yaml", timeout=30)
    response.raise_for_status()
    version_content = response.text
    print("✅ Fetched\n")
    
    print("📝 Updating version manifest...\n")
    version_lines = []
    
    for line in version_content.split('\n'):
        # Skip old metadata
        if line.strip().startswith('ManifestType:') or line.strip().startswith('ManifestVersion:'):
            continue
        
        # Update version
        if 'PackageVersion:' in line:
            line = f'PackageVersion: {version}'
            print(f"✅ Updated PackageVersion")
        
        version_lines.append(line)
    
    # Add manifest metadata
    version_lines.extend(['ManifestType: version', 'ManifestVersion: 1.9.0'])
    
    # Save version manifest
    with open('UniKey.UniKey.yaml', 'w', encoding='utf-8') as f:
        f.write('\n'.join(version_lines))
    print(f"\n✅ Saved: UniKey.UniKey.yaml")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ ALL MANIFESTS CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  1. UniKey.UniKey.installer.yaml")
    print(f"  2. UniKey.UniKey.locale.en-US.yaml")
    print(f"  3. UniKey.UniKey.yaml")
    print(f"\nVersion: {version}")
    print(f"Architectures: x64, x86, arm64")
    print(f"Release Notes: {release_notes}")
    print(f"Release Notes URL: {release_notes_url}")


if __name__ == '__main__':
    main()
