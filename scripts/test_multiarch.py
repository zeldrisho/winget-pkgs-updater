#!/usr/bin/env python3
"""
Test script to verify multi-architecture support in update_manifest.py
Simulates scenario: old version has x64/x86, new version adds arm64
"""

import sys
import os

# Test manifest content (old version without arm64)
old_manifest = """# Created with YamlCreate.ps1
PackageIdentifier: UniKey.UniKey
PackageVersion: 4.6.230919
InstallerType: zip
ReleaseDate: 2023-09-19
Installers:
- Architecture: x64
  NestedInstallerType: portable
  NestedInstallerFiles:
  - RelativeFilePath: UnikeyNT.exe
    PortableCommandAlias: UnikeyNT
  InstallerUrl: https://unikey.org/assets/release/unikey46RC2-230919-win64.zip
  InstallerSha256: OLD_HASH_X64
- Architecture: x86
  NestedInstallerType: portable
  NestedInstallerFiles:
  - RelativeFilePath: UnikeyNT.exe
    PortableCommandAlias: UnikeyNT
  InstallerUrl: https://unikey.org/assets/release/unikey46RC2-230919-win32.zip
  InstallerSha256: OLD_HASH_X86
ManifestType: installer
ManifestVersion: 1.9.0
"""

# Import the functions we need to test
sys.path.insert(0, '/workspaces/winget-pkgs-updater/scripts')
from update_manifest import add_missing_architectures, update_manifest_content

# Test data
arch_hashes = {
    'x64': '667B8D31B0D85FDC2CA17D54C4EAB870BA7269063C1DD53ACEC7897A97AF04E3',
    'x86': '178E3530EFDBE37C10C418AEF5E8DF20740C61BB3548F18E1D8478E333E1BE65',
    'arm64': '6FFDC649C7F449214F9D71DCA1FE6AA37722AC28EA1961752D1F3E3966FEDB1F'
}

installer_urls = {
    'x64': 'https://unikey.org/assets/release/unikey46RC2-230919-win64.zip',
    'x86': 'https://unikey.org/assets/release/unikey46RC2-230919-win32.zip',
    'arm64': 'https://unikey.org/assets/release/unikey46RC2-250531-arm64.zip'
}

print("=" * 60)
print("TEST: Multi-Architecture Support")
print("=" * 60)
print("\n📋 Scenario: Old version has x64/x86, new version adds arm64\n")

# Step 1: Update hashes for existing architectures
print("Step 1: Updating hashes for existing architectures...")
updated_content = update_manifest_content(
    old_manifest,
    version='4.6.250531',
    sha256=None,
    signature_sha256=None,
    release_notes=None,
    release_notes_url=None,
    arch_hashes=arch_hashes
)
print("✅ Step 1 complete\n")

# Step 2: Add missing architectures (arm64)
print("Step 2: Adding missing architectures...")
final_content = add_missing_architectures(
    updated_content,
    arch_hashes,
    installer_urls
)
print("✅ Step 2 complete\n")

# Verify results
print("=" * 60)
print("VERIFICATION:")
print("=" * 60)

# Check if arm64 was added
if 'arm64' in final_content:
    print("✅ arm64 architecture added")
else:
    print("❌ arm64 architecture NOT found")

# Check if all hashes were updated
if arch_hashes['x64'] in final_content:
    print("✅ x64 hash updated correctly")
else:
    print("❌ x64 hash NOT updated")

if arch_hashes['x86'] in final_content:
    print("✅ x86 hash updated correctly")
else:
    print("❌ x86 hash NOT updated")

if arch_hashes['arm64'] in final_content:
    print("✅ arm64 hash added correctly")
else:
    print("❌ arm64 hash NOT found")

# Check if version was updated
if '4.6.250531' in final_content:
    print("✅ Version updated to 4.6.250531")
else:
    print("❌ Version NOT updated")

# Check if old hashes are gone
if 'OLD_HASH_X64' not in final_content and 'OLD_HASH_X86' not in final_content:
    print("✅ Old hashes removed")
else:
    print("❌ Old hashes still present")

print("\n" + "=" * 60)
print("FINAL MANIFEST:")
print("=" * 60)
print(final_content)
