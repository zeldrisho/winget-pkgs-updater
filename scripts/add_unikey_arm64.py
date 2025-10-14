#!/usr/bin/env python3
"""
Add arm64 architecture to UniKey manifest with correct SHA256 hashes
"""

import hashlib
import requests
import tempfile
import yaml
from pathlib import Path


def download_and_hash(url: str) -> str:
    """Download file and calculate SHA256"""
    print(f"📥 Downloading: {url}")
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)
        
        tmp.flush()
        tmp.seek(0)
        
        # Calculate hash
        sha256_hash = hashlib.sha256()
        with open(tmp.name, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        hash_value = sha256_hash.hexdigest().upper()
        print(f"✅ SHA256: {hash_value}")
        
        Path(tmp.name).unlink()  # Delete temp file
        return hash_value


def main():
    """Main entry point"""
    print("🚀 UniKey.UniKey - Adding arm64 architecture\n")
    
    # URLs based on checkver config
    # Build dates: x64/x86 = 230919, arm64 = 250531
    urls = {
        'x64': 'https://unikey.org/assets/release/unikey46RC2-230919-win64.zip',
        'x86': 'https://unikey.org/assets/release/unikey46RC2-230919-win32.zip',
        'arm64': 'https://unikey.org/assets/release/unikey46RC2-250531-arm64.zip'
    }
    
    # Fetch raw manifest from microsoft/winget-pkgs
    print("📡 Fetching manifest from microsoft/winget-pkgs...")
    manifest_url = "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/u/UniKey/UniKey/4.6.230919/UniKey.UniKey.installer.yaml"
    response = requests.get(manifest_url, timeout=30)
    response.raise_for_status()
    manifest_content = response.text
    print("✅ Manifest fetched\n")
    
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
    
    # Update manifest
    print("📝 Updating manifest...\n")
    
    lines = manifest_content.split('\n')
    updated_lines = []
    current_arch = None
    last_installer_idx = -1
    manifest_type_idx = -1
    
    for i, line in enumerate(lines):
        # Track ManifestType line
        if line.strip().startswith('ManifestType:'):
            manifest_type_idx = i
            continue  # Skip for now, will add at end
        
        # Track ManifestVersion line
        if line.strip().startswith('ManifestVersion:'):
            continue  # Skip for now, will add at end
        
        # Track current architecture
        if line.strip().startswith('- Architecture:'):
            current_arch = line.split(':')[1].strip()
            last_installer_idx = len(updated_lines)
        
        # Update SHA256 for current architecture
        if 'InstallerSha256:' in line and current_arch in hashes:
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f'InstallerSha256: {hashes[current_arch]}'
            print(f"✅ Updated {current_arch} hash")
        
        # Update InstallerUrl for architectures
        if 'InstallerUrl:' in line and current_arch:
            if current_arch in urls:
                indent = len(line) - len(line.lstrip())
                line = ' ' * indent + f'InstallerUrl: {urls[current_arch]}'
                print(f"✅ Updated {current_arch} URL")
        
        updated_lines.append(line)
    
    # Add arm64 architecture if not exists
    if 'arm64' not in manifest_content.lower():
        print("\n➕ Adding arm64 architecture...")
        
        # Find where to insert (after last installer)
        # Search backwards for the last line of last installer
        insert_idx = len(updated_lines)
        for i in range(len(updated_lines) - 1, -1, -1):
            line = updated_lines[i].strip()
            if line.startswith('InstallerSha256:') or line.startswith('InstallerUrl:'):
                insert_idx = i + 1
                break
        
        arm64_section = [
            '- Architecture: arm64',
            '  NestedInstallerType: portable',
            '  NestedInstallerFiles:',
            '  - RelativeFilePath: UnikeyNT.exe',
            '    PortableCommandAlias: UnikeyNT',
            f'  InstallerUrl: {urls["arm64"]}',
            f'  InstallerSha256: {hashes["arm64"]}'
        ]
        
        updated_lines = updated_lines[:insert_idx] + arm64_section + updated_lines[insert_idx:]
        print("✅ Added arm64 architecture")
    
    # Add ManifestType and ManifestVersion at the end
    updated_lines.append('ManifestType: installer')
    updated_lines.append('ManifestVersion: 1.9.0')
    
    # Update version to 4.6.250531 (latest build date from arm64)
    final_lines = []
    for line in updated_lines:
        if 'PackageVersion:' in line:
            line = line.replace('4.6.230919', '4.6.250531')
            print("✅ Updated PackageVersion to 4.6.250531")
        final_lines.append(line)
    
    # Save result
    output_path = 'UniKey.UniKey.installer.yaml'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_lines))
    
    print(f"\n✅ Manifest saved to: {output_path}")
    print("\n📄 Preview:")
    print("=" * 60)
    print('\n'.join(final_lines))


if __name__ == '__main__':
    main()
