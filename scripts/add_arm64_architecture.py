#!/usr/bin/env python3
"""
Script to add arm64 architecture to UniKey manifest and calculate correct SHA256 hashes
Fetches raw manifest from microsoft/winget-pkgs and adds arm64 architecture
"""

import re
import sys
import json
import yaml
import hashlib
import requests
import tempfile
from pathlib import Path


def download_file(url: str, filepath: str) -> bool:
    """Download file from URL to filepath"""
    try:
        print(f"📥 Downloading: {url}")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error downloading {url}: {e}")
        return False


def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 hash of file"""
    print(f"🔐 Calculating SHA256 for: {filepath}")
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    hash_value = sha256_hash.hexdigest().upper()
    print(f"✅ SHA256: {hash_value}")
    return hash_value


def fetch_github_file(repo: str, path: str, branch: str = "master") -> str:
    """Fetch file content from GitHub"""
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    print(f"📡 Fetching: {url}")
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            print(f"✅ Fetched from GitHub")
            return response.text
        else:
            print(f"❌ Failed to fetch: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching {url}: {e}")
        return None


def load_checkver_config(config_path: str) -> dict:
    """Load checkver configuration"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def extract_metadata_from_regex(script_output: str, regex_pattern: str) -> dict:
    """Extract metadata using named groups in regex"""
    match = re.search(regex_pattern, script_output)
    if not match:
        return {}
    
    # Get all named groups
    metadata = match.groupdict()
    return metadata


def build_installer_urls(config: dict, metadata: dict) -> dict:
    """Build installer URLs for each architecture using template and metadata"""
    url_template = config.get('installerUrlTemplate', {})
    
    if isinstance(url_template, str):
        # Single URL template (not multi-arch)
        return {'single': url_template.format(**metadata)}
    
    # Multi-arch URL templates
    urls = {}
    for arch, template in url_template.items():
        urls[arch] = template.format(**metadata)
    
    return urls


def update_installer_manifest_with_hashes(content: str, hashes: dict, metadata: dict) -> str:
    """Update installer manifest with correct SHA256 hashes for each architecture"""
    lines = content.split('\n')
    updated_lines = []
    current_arch = None
    
    for i, line in enumerate(lines):
        # Detect architecture
        if re.match(r'^-\s*Architecture:\s*(\w+)', line):
            match = re.match(r'^-\s*Architecture:\s*(\w+)', line)
            current_arch = match.group(1)
        
        # Update InstallerUrl with correct metadata
        if 'InstallerUrl:' in line and current_arch:
            # Replace URL with correct one from metadata
            indent = len(line) - len(line.lstrip())
            url_template = metadata.get(f'installer_url_{current_arch}', '')
            if url_template:
                line = ' ' * indent + f'InstallerUrl: {url_template}'
        
        # Update SHA256 hash
        if 'InstallerSha256:' in line and current_arch and current_arch in hashes:
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f'InstallerSha256: {hashes[current_arch]}'
        
        updated_lines.append(line)
    
    return '\n'.join(updated_lines)


def add_arm64_architecture(content: str, arm64_url: str, arm64_hash: str) -> str:
    """Add arm64 architecture to installer manifest"""
    lines = content.split('\n')
    
    # Find the last installer entry
    last_installer_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('- Architecture:'):
            # Find the end of this installer block (next field at same level or end of installers)
            for j in range(i + 1, len(lines)):
                if lines[j].strip().startswith('- Architecture:') or \
                   (lines[j].strip() and not lines[j].startswith('  ') and not lines[j].startswith('-')):
                    last_installer_idx = j - 1
                    break
            if last_installer_idx == -1:
                last_installer_idx = len(lines) - 1
            break
    
    if last_installer_idx == -1:
        print("❌ Could not find installer section")
        return content
    
    # Extract the structure of the last installer (x86 or x64)
    installer_start = -1
    for i in range(last_installer_idx, -1, -1):
        if lines[i].strip().startswith('- Architecture:'):
            installer_start = i
            break
    
    # Copy the structure and modify for arm64
    arm64_lines = []
    for i in range(installer_start, last_installer_idx + 1):
        line = lines[i]
        
        # Replace architecture
        if 'Architecture:' in line:
            line = re.sub(r'Architecture:\s*\w+', 'Architecture: arm64', line)
        
        # Replace URL
        elif 'InstallerUrl:' in line:
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f'InstallerUrl: {arm64_url}'
        
        # Replace SHA256
        elif 'InstallerSha256:' in line:
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f'InstallerSha256: {arm64_hash}'
        
        arm64_lines.append(line)
    
    # Insert arm64 section after the last installer
    lines = lines[:last_installer_idx + 1] + arm64_lines + lines[last_installer_idx + 1:]
    
    return '\n'.join(lines)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python add_arm64_architecture.py <checkver_config.yaml>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Load checkver config
    print(f"📄 Loading checkver config: {config_path}")
    config = load_checkver_config(config_path)
    
    package_id = config['packageIdentifier']
    manifest_path = config['manifestPath']
    
    print(f"📦 Package: {package_id}")
    print(f"📂 Manifest path: {manifest_path}")
    
    # Get latest version from microsoft/winget-pkgs
    print(f"\n🔍 Finding latest version in microsoft/winget-pkgs...")
    
    # List versions
    api_url = f"https://api.github.com/repos/microsoft/winget-pkgs/contents/{manifest_path}"
    response = requests.get(api_url, timeout=30)
    if response.status_code != 200:
        print(f"❌ Failed to list versions: HTTP {response.status_code}")
        sys.exit(1)
    
    versions = [item['name'] for item in response.json() if item['type'] == 'dir']
    
    # Sort versions and get latest
    # Use a robust sorting key that handles both numeric versions (1.2.3) and date-based versions (2025.10.13)
    def version_sort_key(v):
        try:
            return [int(x) for x in v.split('.')]
        except ValueError:
            # If conversion fails, try to sort as strings (fallback)
            return [x for x in v.split('.')]
    
    versions.sort(key=version_sort_key)
    latest_version = versions[-1]
    
    print(f"✅ Latest version: {latest_version}")
    
    # Fetch installer manifest
    installer_manifest_path = f"{manifest_path}/{latest_version}/{package_id}.installer.yaml"
    manifest_content = fetch_github_file('microsoft/winget-pkgs', installer_manifest_path)
    
    if not manifest_content:
        print("❌ Failed to fetch installer manifest")
        sys.exit(1)
    
    # Check version from checkver script
    print(f"\n🔍 Checking for new version using checkver script...")
    import subprocess
    
    result = subprocess.run(
        ['python3', 'scripts/check_version.py', config_path],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Checkver script failed: {result.stderr}")
        sys.exit(1)
    
    # Parse version info - extract JSON from output
    output = result.stdout
    json_start = output.find('{')
    if json_start == -1:
        print(f"❌ No JSON found in output")
        sys.exit(1)
    
    json_str = output[json_start:]
    version_info = json.loads(json_str)
    print(f"✅ New version detected: {version_info['version']}")
    print(f"📋 Metadata: {json.dumps(version_info.get('metadata', {}), indent=2)}")
    
    # Build URLs for each architecture
    metadata = version_info.get('metadata', {})
    metadata['version'] = version_info['version']
    
    url_template = config.get('installerUrlTemplate', {})
    
    if not isinstance(url_template, dict):
        print("❌ installerUrlTemplate must be a dict for multi-arch support")
        sys.exit(1)
    
    # Build URLs
    urls = {}
    for arch, template in url_template.items():
        urls[arch] = template.format(**metadata)
        print(f"🔗 {arch}: {urls[arch]}")
    
    # Download and calculate hashes
    print(f"\n🔐 Calculating SHA256 hashes for each architecture...")
    hashes = {}
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for arch, url in urls.items():
            filename = Path(url).name
            filepath = Path(temp_dir) / filename
            
            if download_file(url, str(filepath)):
                hashes[arch] = calculate_sha256(str(filepath))
            else:
                print(f"⚠️  Skipping {arch} - download failed")
    
    if not hashes:
        print("❌ No hashes calculated")
        sys.exit(1)
    
    print(f"\n✅ Calculated hashes:")
    for arch, hash_value in hashes.items():
        print(f"  {arch}: {hash_value}")
    
    # Update manifest with correct URLs and hashes
    print(f"\n📝 Updating manifest...")
    
    # Add arm64 if it exists in hashes but not in manifest
    if 'arm64' in hashes and 'arm64' not in manifest_content.lower():
        print("➕ Adding arm64 architecture...")
        manifest_content = add_arm64_architecture(manifest_content, urls['arm64'], hashes['arm64'])
    
    # Update all hashes
    manifest_content = update_installer_manifest_with_hashes(manifest_content, hashes, urls)
    
    # Save updated manifest
    output_path = f"{package_id}.installer.yaml"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(manifest_content)
    
    print(f"✅ Updated manifest saved to: {output_path}")
    print(f"\n📄 Preview:")
    print("=" * 60)
    print(manifest_content)


if __name__ == '__main__':
    main()
