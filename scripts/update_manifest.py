#!/usr/bin/env python3
"""
Update WinGet manifest with new version and SHA256
Fetches existing manifest from microsoft/winget-pkgs, updates it, and creates PR
"""

import os
import re
import sys
import json
import yaml
import hashlib
import requests
import tempfile
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def check_existing_pr(package_id: str, version: str) -> bool:
    """
    Check if PR already exists for this package version.
    Returns True if OPEN or MERGED PR exists (should skip), False otherwise (should create).
    Note: CLOSED PRs are ignored - we can retry them.
    
    Supports both PR title formats:
    - "New version: {package_id} version {version}"
    - "Update {package_id} to {version}"
    """
    try:
        # Search for PRs that contain both package ID and version
        # This catches both "New version: X version Y" and "Update X to Y" formats
        search_query = f"{package_id} {version} in:title"
        print(f"🔍 Checking for existing PRs: {package_id} version {version}")
        
        result = subprocess.run(
            [
                'gh', 'pr', 'list',
                '--repo', 'microsoft/winget-pkgs',
                '--search', search_query,
                '--state', 'all',  # Check open, merged, and closed PRs
                '--json', 'number,title,state',
                '--limit', '10'
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            prs = json.loads(result.stdout)
            if prs:
                for pr in prs:
                    # Check if title contains both package ID and version
                    # This matches both formats:
                    # - "New version: {package_id} version {version}"
                    # - "Update {package_id} to {version}"
                    title_lower = pr['title'].lower()
                    if package_id.lower() in title_lower and version in pr['title']:
                        state = pr['state']
                        state_emoji = "🟢" if state == "OPEN" else "🟣" if state == "MERGED" else "⚪"
                        
                        # Only skip for OPEN or MERGED PRs
                        if state in ["OPEN", "MERGED"]:
                            print(f"⏭️  {state_emoji} PR already exists: #{pr['number']} ({state})")
                            print(f"   Title: {pr['title']}")
                            print(f"   URL: https://github.com/microsoft/winget-pkgs/pull/{pr['number']}")
                            print(f"   Skipping - PR is {state}")
                            return True  # Skip - PR exists and is open/merged
                        else:
                            # CLOSED PR - we can retry
                            print(f"   ⚪ Found CLOSED PR: #{pr['number']}")
                            print(f"   URL: https://github.com/microsoft/winget-pkgs/pull/{pr['number']}")
                            print(f"   Will create new PR (closed PRs can be retried)")
        
        print("✅ No active PR found - will create new one")
        return False  # No active PR found - should create
        
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not check existing PRs: {e}")
        print("Continuing anyway...")
        return False  # Continue on error


def download_file(url: str, filepath: str) -> bool:
    """Download file from URL to filepath with validation"""
    try:
        print(f"Downloading: {url}")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Track downloaded size
        total_size = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    total_size += len(chunk)
        
        # Verify file was downloaded
        if not os.path.exists(filepath):
            print(f"Error: File was not created: {filepath}")
            return False
        
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            print(f"Error: Downloaded file is empty")
            return False
        
        print(f"Downloaded to: {filepath} ({file_size:,} bytes)")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        return False


def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 hash of file with validation"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    file_size = os.path.getsize(filepath)
    if file_size == 0:
        raise ValueError(f"File is empty: {filepath}")
    
    sha256_hash = hashlib.sha256()
    bytes_read = 0
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            bytes_read += len(byte_block)
    
    if bytes_read != file_size:
        raise ValueError(f"File size mismatch: expected {file_size}, read {bytes_read}")
    
    hash_value = sha256_hash.hexdigest().upper()
    print(f"  Calculated SHA256 for {os.path.basename(filepath)} ({file_size:,} bytes): {hash_value}")
    return hash_value


def remove_duplicate_fields(content: str) -> str:
    """
    Remove duplicate fields in YAML content while preserving structure.
    For each unique field name within a context (architecture, top-level, etc.),
    keeps only the first occurrence and removes duplicates.
    
    Smart detection:
    - Tracks context: top-level, within architecture blocks, within other sections
    - Preserves list items (multiple '- Architecture:' is intentional)
    - Only removes actual duplicates (same field name in same context)
    - Each architecture block is tracked separately
    """
    lines = content.split('\n')
    result_lines = []
    
    # Track field occurrences per context
    # Format: {context_key: {field_name: count}}
    field_tracker = {}
    
    # Track current context
    current_arch = None
    current_section = None
    current_list_item_idx = 0  # Track which list item we're in
    in_installer_list = False
    indent_stack = []  # Track indentation levels
    
    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            result_lines.append(line)
            continue
        
        # Calculate indentation
        indent = len(line) - len(line.lstrip())
        
        # Detect Installers section
        if stripped == 'Installers:':
            in_installer_list = True
            current_list_item_idx = 0
            result_lines.append(line)
            continue
        
        # Parse field name
        if ':' in stripped:
            field_match = stripped.split(':', 1)[0].strip('- ')
            field_name = field_match
            is_list_start = stripped.startswith('- ')
            
            # Detect new list item in Installers section
            if in_installer_list and is_list_start and field_name == 'Architecture':
                current_list_item_idx += 1
                arch_match = stripped.split(':', 1)[1].strip()
                current_arch = arch_match
                # Reset field tracker for this new architecture block
                context_key = f"arch_block:{current_list_item_idx}:{current_arch}"
                field_tracker[context_key] = {}
                result_lines.append(line)
                continue
            
            # Detect context changes (exit Installers section)
            if indent == 0 and not stripped.startswith('- '):
                in_installer_list = False
                current_arch = None
                current_section = field_name
                current_list_item_idx = 0
            
            # Build context key
            if current_arch and in_installer_list:
                # Inside a specific architecture block
                context_key = f"arch_block:{current_list_item_idx}:{current_arch}"
            elif is_list_start:
                # List item at this indent level (e.g., AppsAndFeaturesEntries)
                context_key = f"list_item:{indent}:{line_idx}"
            elif current_section:
                context_key = f"section:{current_section}:{indent}"
            else:
                context_key = f"top:{indent}"
            
            # Check if this is a duplicate (but not for list-starting fields like '- Architecture')
            if not (is_list_start and field_name == 'Architecture'):
                # Initialize tracker for this context
                if context_key not in field_tracker:
                    field_tracker[context_key] = {}
                
                # Check if field already seen in this context
                if field_name in field_tracker[context_key]:
                    # Duplicate detected - skip this line
                    field_tracker[context_key][field_name] += 1
                    context_desc = context_key.split(':')[0]
                    if current_arch:
                        context_desc = f"{current_arch} architecture"
                    print(f"  🧹 Removed duplicate '{field_name}' in {context_desc} (occurrence #{field_tracker[context_key][field_name]})")
                    continue
                else:
                    # First occurrence - track it
                    field_tracker[context_key][field_name] = 1
            
        result_lines.append(line)
    
    # Clean up multiple consecutive blank lines
    result = '\n'.join(result_lines)
    result = re.sub(r'\n\s*\n\s*\n+', '\n\n', result)
    
    return result


def validate_yaml_content(content: str, filepath: str = "manifest") -> bool:
    """
    Validate YAML content and check for duplicate keys.
    Returns True if valid, False otherwise.
    """
    try:
        # Try to parse the YAML
        parsed = yaml.safe_load(content)
        
        # Check for common issues
        lines = content.split('\n')
        field_counts = {}
        current_section = None
        
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # Track sections
            if stripped and not stripped.startswith('#') and ':' in stripped:
                if not line.startswith(' '):  # Top-level field
                    current_section = 'top_level'
                
                # Count field occurrences (simple check)
                field_name = stripped.split(':')[0].strip('- ')
                key = f"{current_section}:{field_name}"
                field_counts[key] = field_counts.get(key, 0) + 1
        
        # Report duplicates
        has_duplicates = False
        for key, count in field_counts.items():
            if count > 1:
                section, field = key.split(':', 1)
                print(f"  ⚠️  Warning: Field '{field}' appears {count} times in {section}")
                has_duplicates = True
        
        if has_duplicates:
            print(f"  ℹ️  Note: Some duplicate fields were detected but may be intentional (e.g., in lists)")
        
        return True
        
    except yaml.YAMLError as e:
        print(f"  ❌ YAML validation error in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Validation error in {filepath}: {e}")
        return False


def calculate_msix_signature_sha256(msix_path: str) -> Optional[str]:
    """
    Calculate SHA256 of MSIX signature using PowerShell.
    Returns None if calculation fails.
    """
    try:
        ps_script = f'''
$packagePath = "{msix_path}"
$sigPath = [System.IO.Path]::GetTempFileName()
$appxFile = Get-AppxPackage -Path $packagePath -PackageTypeFilter Bundle,Main,Resource | Select-Object -First 1
if ($appxFile) {{
    $signHash = (Get-AuthenticodeSignature $packagePath).SignerCertificate.GetCertHashString("SHA256")
    Write-Output $signHash
}} else {{
    # Alternative method: Extract signature from MSIX
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($packagePath)
    $sigFile = $zip.Entries | Where-Object {{ $_.FullName -eq "AppxSignature.p7x" }}
    if ($sigFile) {{
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($sigFile, $sigPath, $true)
        $sigHash = (Get-FileHash -Path $sigPath -Algorithm SHA256).Hash
        Write-Output $sigHash
    }}
    $zip.Dispose()
    Remove-Item $sigPath -ErrorAction SilentlyContinue
}}
'''
        
        result = subprocess.run(
            ['pwsh', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            sig_hash = result.stdout.strip().upper()
            print(f"Calculated SignatureSha256: {sig_hash}")
            return sig_hash
        else:
            print(f"Warning: Could not calculate SignatureSha256: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Warning: Error calculating SignatureSha256: {e}")
        return None


def extract_product_code_from_msi(msi_path: str) -> Optional[str]:
    """
    Extract ProductCode from MSI file using msitools.
    Returns ProductCode in format {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
    Returns None if extraction fails.
    """
    try:
        # Use msiinfo to extract Property table from MSI
        result = subprocess.run(
            ['msiinfo', 'export', msi_path, 'Property'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout:
            # Parse output to find ProductCode
            # Format: ProductCode\t{GUID}
            for line in result.stdout.split('\n'):
                if line.startswith('ProductCode'):
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        product_code = parts[1].strip()
                        print(f"  Extracted ProductCode: {product_code}")
                        return product_code
        else:
            print(f"  Warning: Could not extract ProductCode: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("  Warning: msitools not installed. Cannot extract ProductCode.")
        print("  Install with: sudo apt-get install msitools")
        return None
    except Exception as e:
        print(f"  Warning: Error extracting ProductCode: {e}")
        return None


def fetch_github_file(repo: str, path: str, branch: str = "master") -> Optional[str]:
    """Fetch file content from GitHub"""
    url = f"https://raw.githubusercontent.com/{repo}/{branch}/{path}"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None


def update_manifest_content(
    content: str, 
    version: str, 
    sha256: Optional[str] = None, 
    signature_sha256: Optional[str] = None,
    release_notes: Optional[str] = None,
    release_notes_url: Optional[str] = None,
    arch_hashes: Optional[Dict[str, str]] = None,
    installer_urls: Optional[Dict[str, str]] = None,
    installer_url: Optional[str] = None,
    product_codes: Optional[Dict[str, str]] = None
) -> str:
    """
    Update version, InstallerUrl, SHA256, and ProductCode in manifest content.
    
    Strategy:
    1. Extract old version from PackageVersion field
    2. Replace ALL occurrences of old version with new version
    3. Update SHA256 hashes if provided (supports multi-arch)
    4. Update ProductCode if provided (supports multi-arch)
    5. Automatically update ReleaseDate to today (if field exists in old manifest)
    6. Automatically update ReleaseNotes and ReleaseNotesUrl (if fields exist in old manifest)
    
    Note: Fields are only updated if they already exist in the old manifest.
    No need to define updateMetadata in checkver.yaml - system automatically syncs all fields.
    """
    
    # Extract old version from PackageVersion field
    old_version = None
    version_match = re.search(r'PackageVersion:\s*([\d\.]+)', content)
    if version_match:
        old_version = version_match.group(1)
        print(f"  Detected old version: {old_version}")
        print(f"  Updating to new version: {version}")
    
    # Replace ALL occurrences of old version with new version
    # This handles: PackageVersion, InstallerUrl, DisplayName, etc.
    if old_version and old_version != version:
        # Count occurrences before replacement
        count = content.count(old_version)
        print(f"  Found {count} occurrences of version {old_version}")
        
        # Replace all occurrences of full version
        content = content.replace(old_version, version)
        print(f"  ✅ Replaced all occurrences with {version}")
        
        # Also replace short version (e.g., 2.3.12 -> 2.4.4 for URL tags)
        # Only if version ends with .0
        if old_version.endswith('.0') and version.endswith('.0'):
            old_short = old_version[:-2]  # Remove trailing .0
            new_short = version[:-2]      # Remove trailing .0
            short_count = content.count(old_short)
            if short_count > 0:
                content = content.replace(old_short, new_short)
                print(f"  ✅ Also replaced {short_count} occurrences of short version {old_short} with {new_short}")
    
    # Update InstallerUrl - handle both single and multi-architecture
    if installer_urls:
        # Multi-architecture: update URL for each architecture
        lines = content.split('\n')
        updated_lines = []
        current_arch = None
        updated_archs = set()  # Track which architectures have been updated
        
        for line in lines:
            # Track current architecture
            if re.match(r'^\s*-\s*Architecture:\s*(\w+)', line):
                match = re.match(r'^\s*-\s*Architecture:\s*(\w+)', line)
                current_arch = match.group(1)
            
            # Update URL for current architecture (only once per architecture)
            if 'InstallerUrl:' in line and current_arch and current_arch in installer_urls:
                if current_arch not in updated_archs:
                    indent = len(line) - len(line.lstrip())
                    line = ' ' * indent + f'InstallerUrl: {installer_urls[current_arch]}'
                    print(f"  ✅ Updated {current_arch} InstallerUrl")
                    updated_archs.add(current_arch)
                else:
                    # Duplicate field detected - remove it
                    print(f"  ⚠️  Removed duplicate InstallerUrl for {current_arch}")
                    continue  # Skip this line
            
            updated_lines.append(line)
        
        content = '\n'.join(updated_lines)
        # Clean up multiple consecutive blank lines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    elif installer_url:
        # Single architecture: replace the entire InstallerUrl
        content = re.sub(
            r'InstallerUrl:\s*https?://[^\s]+',
            f'InstallerUrl: {installer_url}',
            content
        )
        print(f"  ✅ Updated InstallerUrl")
    
    # Update InstallerSha256 - support multi-architecture
    if arch_hashes:
        # Multi-architecture: update hash for each architecture
        lines = content.split('\n')
        updated_lines = []
        current_arch = None
        updated_archs = set()  # Track which architectures have been updated
        
        for line in lines:
            # Track current architecture
            if re.match(r'^\s*-\s*Architecture:\s*(\w+)', line):
                match = re.match(r'^\s*-\s*Architecture:\s*(\w+)', line)
                current_arch = match.group(1)
            
            # Update hash for current architecture (only once per architecture)
            if 'InstallerSha256:' in line and current_arch and current_arch in arch_hashes:
                if current_arch not in updated_archs:
                    indent = len(line) - len(line.lstrip())
                    line = ' ' * indent + f'InstallerSha256: {arch_hashes[current_arch]}'
                    print(f"  ✅ Updated {current_arch} InstallerSha256")
                    updated_archs.add(current_arch)
                else:
                    # Duplicate field detected - remove it
                    print(f"  ⚠️  Removed duplicate InstallerSha256 for {current_arch}")
                    continue  # Skip this line
            
            updated_lines.append(line)
        
        content = '\n'.join(updated_lines)
        # Clean up multiple consecutive blank lines
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    elif sha256:
        # Single architecture (legacy)
        content = re.sub(
            r'InstallerSha256:\s*[A-Fa-f0-9]+',
            f'InstallerSha256: {sha256}',
            content
        )
        print(f"  ✅ Updated InstallerSha256")
    
    # Update SignatureSha256 if provided (for MSIX packages)
    if signature_sha256:
        content = re.sub(
            r'SignatureSha256:\s*[A-Fa-f0-9]+',
            f'SignatureSha256: {signature_sha256}',
            content
        )
        print(f"  ✅ Updated SignatureSha256")
    
    # Update ProductCode - support multi-architecture and AppsAndFeaturesEntries
    if product_codes:
        # Multi-architecture: update ProductCode for each architecture
        lines = content.split('\n')
        updated_lines = []
        current_arch = None
        in_apps_features = False
        in_installers_section = False
        updated_contexts = set()  # Track which contexts have been updated (e.g., "apps_features", "x64", "x86")
        
        for line in lines:
            # Track if we're in the Installers section (for multi-arch)
            if 'Installers:' in line and line.strip() == 'Installers:':
                in_installers_section = True
                in_apps_features = False
            
            # Track current architecture (only in Installers section)
            if in_installers_section and re.match(r'^\s*-\s*Architecture:\s*(\w+)', line):
                match = re.match(r'^\s*-\s*Architecture:\s*(\w+)', line)
                current_arch = match.group(1)
            
            # Track if we're in AppsAndFeaturesEntries section
            if 'AppsAndFeaturesEntries:' in line:
                in_apps_features = True
                in_installers_section = False
                current_arch = None
            elif line and not line.startswith(' ') and not line.startswith('-'):
                # Exited both sections
                if not line.strip().startswith('#'):
                    in_apps_features = False
                    in_installers_section = False
            
            # Update ProductCode in different contexts
            # Note: ProductCode must be quoted in YAML (like UpgradeCode)
            if 'ProductCode:' in line:
                indent = len(line) - len(line.lstrip())
                context_key = None
                should_update = False
                
                if in_apps_features and 'default' in product_codes:
                    context_key = 'apps_features'
                    if context_key not in updated_contexts:
                        # ProductCode in AppsAndFeaturesEntries (single-arch)
                        line = ' ' * indent + f"- ProductCode: '{product_codes['default']}'"
                        print(f"  ✅ Updated ProductCode in AppsAndFeaturesEntries")
                        should_update = True
                    else:
                        print(f"  ⚠️  Removed duplicate ProductCode in AppsAndFeaturesEntries")
                        continue
                elif in_installers_section and current_arch and current_arch in product_codes:
                    context_key = f'installer_{current_arch}'
                    if context_key not in updated_contexts:
                        # ProductCode for specific architecture in Installers section
                        line = ' ' * indent + f"ProductCode: '{product_codes[current_arch]}'"
                        print(f"  ✅ Updated {current_arch} ProductCode in Installers")
                        should_update = True
                    else:
                        print(f"  ⚠️  Removed duplicate ProductCode for {current_arch} in Installers")
                        continue
                elif not in_apps_features and not in_installers_section and 'default' in product_codes:
                    context_key = 'top_level'
                    if context_key not in updated_contexts:
                        # Top-level ProductCode (single-arch, before Installers section)
                        line = ' ' * indent + f"ProductCode: '{product_codes['default']}'"
                        print(f"  ✅ Updated top-level ProductCode")
                        should_update = True
                    else:
                        print(f"  ⚠️  Removed duplicate top-level ProductCode")
                        continue
                elif current_arch and current_arch in product_codes:
                    context_key = f'fallback_{current_arch}'
                    if context_key not in updated_contexts:
                        # Fallback for architecture-specific ProductCode
                        line = ' ' * indent + f"ProductCode: '{product_codes[current_arch]}'"
                        print(f"  ✅ Updated {current_arch} ProductCode")
                        should_update = True
                    else:
                        print(f"  ⚠️  Removed duplicate ProductCode for {current_arch}")
                        continue
                
                if should_update and context_key:
                    updated_contexts.add(context_key)
            
            updated_lines.append(line)
        
        content = '\n'.join(updated_lines)
    
    # Update ReleaseDate to today (ISO 8601 format: YYYY-MM-DD)
    # Only updates if ReleaseDate field already exists in manifest
    today = datetime.now().strftime('%Y-%m-%d')
    if re.search(r'ReleaseDate:\s*[\d-]+', content):
        # Use a function to replace only the first occurrence
        count = [0]  # Mutable container to track count
        def replace_release_date(match):
            count[0] += 1
            if count[0] == 1:
                return f'ReleaseDate: {today}'
            else:
                print(f"  ⚠️  Removed duplicate ReleaseDate (occurrence #{count[0]})")
                return ''  # Remove duplicate
        
        content = re.sub(
            r'ReleaseDate:\s*[\d-]+',
            replace_release_date,
            content
        )
        # Clean up empty lines left by removed duplicates
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        if count[0] > 0:
            print(f"  ✅ Updated ReleaseDate to {today}")
            if count[0] > 1:
                print(f"     (Removed {count[0] - 1} duplicate(s))")
    
    # Update ReleaseNotes if provided AND field already exists in manifest
    # Only updates if ReleaseNotes field already exists in manifest (typically in locale manifest)
    if release_notes and re.search(r'ReleaseNotes:', content):
        # Escape special characters for YAML block scalar
        # Use |- for literal block scalar (strips trailing newlines)
        yaml_notes = release_notes.replace('\r\n', '\n').replace('\r', '\n')
        
        # Replace ReleaseNotes field (handles both single line and block scalar)
        if re.search(r'ReleaseNotes:\s*\|-', content):
            # Block scalar format - replace everything until next field
            # Use a counter to replace only first occurrence
            count = [0]
            def replace_notes_block(match):
                count[0] += 1
                if count[0] == 1:
                    return f'ReleaseNotes: |-\n  {yaml_notes.replace(chr(10), chr(10) + "  ")}\n'
                else:
                    print(f"  ⚠️  Removed duplicate ReleaseNotes block (occurrence #{count[0]})")
                    return ''
            
            content = re.sub(
                r'ReleaseNotes:\s*\|-\n(?:.*\n)*?(?=\w+:)',
                replace_notes_block,
                content,
                flags=re.MULTILINE
            )
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            if count[0] > 0:
                print(f"  ✅ Updated ReleaseNotes (block scalar)")
        else:
            # Single line format - update first occurrence only
            count = [0]
            def replace_notes_line(match):
                count[0] += 1
                if count[0] == 1:
                    return f'ReleaseNotes: |-\n  {yaml_notes.replace(chr(10), chr(10) + "  ")}'
                else:
                    print(f"  ⚠️  Removed duplicate ReleaseNotes (occurrence #{count[0]})")
                    return ''
            
            content = re.sub(
                r'(ReleaseNotes:).*',
                replace_notes_line,
                content
            )
            content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
            if count[0] > 0:
                print(f"  ✅ Updated ReleaseNotes")
    
    # Update ReleaseNotesUrl if provided AND field already exists in manifest
    # Only updates if ReleaseNotesUrl field already exists in manifest (typically in locale manifest)
    if release_notes_url and re.search(r'ReleaseNotesUrl:', content):
        count = [0]
        def replace_notes_url(match):
            count[0] += 1
            if count[0] == 1:
                return f'ReleaseNotesUrl: {release_notes_url}'
            else:
                print(f"  ⚠️  Removed duplicate ReleaseNotesUrl (occurrence #{count[0]})")
                return ''
        
        content = re.sub(
            r'ReleaseNotesUrl:.*',
            replace_notes_url,
            content
        )
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        if count[0] > 0:
            print(f"  ✅ Updated ReleaseNotesUrl")
    
    # Final cleanup: Remove any remaining duplicate fields
    # This is a generic cleanup that catches duplicates we might have missed
    content = remove_duplicate_fields(content)
    
    return content


def clone_winget_pkgs(fork_repo: str, temp_dir: str, token: str) -> bool:
    """Clone forked winget-pkgs repository and sync with upstream"""
    try:
        # Use token in URL for authentication
        repo_url = f"https://{token}@github.com/{fork_repo}.git"
        print(f"Cloning https://github.com/{fork_repo}.git...")
        
        # Clone with more depth to ensure we get recent versions
        subprocess.run(
            ['git', 'clone', '--depth', '50', repo_url, temp_dir],
            check=True,
            capture_output=True
        )
        
        # Add upstream remote and fetch latest
        print(f"Syncing with upstream microsoft/winget-pkgs...")
        subprocess.run(
            ['git', 'remote', 'add', 'upstream', 'https://github.com/microsoft/winget-pkgs.git'],
            cwd=temp_dir,
            check=True,
            capture_output=True
        )
        
        # Fetch upstream master branch (shallow to avoid too much data)
        subprocess.run(
            ['git', 'fetch', 'upstream', 'master', '--depth', '50'],
            cwd=temp_dir,
            check=True,
            capture_output=True
        )
        
        # Merge upstream/master into current branch
        print(f"Merging latest changes from upstream...")
        result = subprocess.run(
            ['git', 'merge', 'upstream/master', '--no-edit', '--strategy-option', 'theirs'],
            cwd=temp_dir,
            capture_output=True
        )
        
        if result.returncode != 0:
            # If merge failed, try reset to upstream/master
            print(f"⚠️  Merge failed, resetting to upstream/master...")
            subprocess.run(
                ['git', 'reset', '--hard', 'upstream/master'],
                cwd=temp_dir,
                check=True,
                capture_output=True
            )
        else:
            print(f"✅ Successfully synced with upstream")
        
        # Configure git
        subprocess.run(
            ['git', 'config', 'user.name', 'github-actions[bot]'],
            cwd=temp_dir,
            check=True
        )
        subprocess.run(
            ['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'],
            cwd=temp_dir,
            check=True
        )
        
        return True
    except Exception as e:
        print(f"Error cloning repository: {e}", file=sys.stderr)
        return False


def create_pr_branch(repo_dir: str, package_id: str, version: str) -> str:
    """Create and checkout new branch for PR"""
    branch_name = f"{package_id}-{version}"
    try:
        subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=repo_dir,
            check=True,
            capture_output=True
        )
        return branch_name
    except Exception as e:
        print(f"Error creating branch: {e}", file=sys.stderr)
        raise


def add_missing_architectures(content: str, arch_hashes: Dict[str, str], installer_urls: Dict[str, str]) -> str:
    """
    Add new architectures to installer manifest if they don't exist.
    For example, add arm64 if version only has x64/x86.
    """
    # Find existing architectures in manifest
    existing_archs = set()
    for line in content.split('\n'):
        if re.match(r'^\s*-\s*Architecture:\s*(\w+)', line):
            match = re.match(r'^\s*-\s*Architecture:\s*(\w+)', line)
            existing_archs.add(match.group(1))
    
    # Find missing architectures
    new_archs = set(arch_hashes.keys()) - existing_archs
    
    if not new_archs:
        return content  # No new architectures to add
    
    print(f"  ➕ Adding new architectures: {', '.join(new_archs)}")
    
    lines = content.split('\n')
    
    # Find where to insert new architectures (before ManifestType)
    insert_idx = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('ManifestType:'):
            insert_idx = i
            break
    
    # Get the structure of the last installer block for reference
    last_installer_start = -1
    last_installer_end = -1
    
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip().startswith('- Architecture:'):
            last_installer_start = i
            # Find end of this installer block
            for j in range(i + 1, len(lines)):
                line = lines[j].strip()
                if line.startswith('- Architecture:') or line.startswith('ManifestType:') or (line and not lines[j].startswith(' ')):
                    last_installer_end = j - 1
                    break
            if last_installer_end == -1:
                last_installer_end = len(lines) - 1
            break
    
    if last_installer_start == -1:
        print("  ⚠️  Could not find existing installer block structure")
        return content
    
    # Extract the structure from the last installer (for NestedInstallerType, etc.)
    installer_template = []
    nested_installer_lines = []
    in_nested = False
    
    for i in range(last_installer_start, min(last_installer_end + 1, len(lines))):
        line = lines[i]
        if 'NestedInstallerType:' in line:
            in_nested = True
            nested_installer_lines.append(line)
        elif in_nested and (line.startswith('  ') and not line.startswith('  InstallerUrl:') and not line.startswith('  InstallerSha256:')):
            nested_installer_lines.append(line)
        elif 'InstallerUrl:' in line or 'InstallerSha256:' in line:
            in_nested = False
    
    # Build new architecture sections
    new_sections = []
    for arch in sorted(new_archs):  # Sort for consistency
        arch_section = [f'- Architecture: {arch}']
        
        # Add nested installer structure if found
        if nested_installer_lines:
            arch_section.extend(nested_installer_lines)
        
        # Add URL and hash
        arch_section.append(f'  InstallerUrl: {installer_urls[arch]}')
        arch_section.append(f'  InstallerSha256: {arch_hashes[arch]}')
        
        new_sections.extend(arch_section)
        print(f"  ✅ Added {arch} architecture")
    
    # Insert new sections before ManifestType
    lines = lines[:insert_idx] + new_sections + lines[insert_idx:]
    
    return '\n'.join(lines)


def process_template_and_create_version(
    repo_dir: str,
    manifest_path: str,
    version: str,
    latest_dir: str,
    latest_version: str,
    sha256: Optional[str],
    signature_sha256: Optional[str],
    release_notes: Optional[str],
    release_notes_url: Optional[str],
    arch_hashes: Optional[Dict[str, str]],
    installer_urls: Optional[Dict[str, str]],
    installer_url: Optional[str],
    product_codes: Optional[Dict[str, str]] = None
) -> bool:
    """
    Copy and update manifest files from template to new version.
    This function is extracted to allow processing template from temporary directory.
    """
    try:
        version_dir = os.path.join(repo_dir, manifest_path, version)
        
        print(f"Copying from latest version: {latest_version}")
        
        # Create new version directory
        os.makedirs(version_dir, exist_ok=True)
        
        # Copy and update each manifest file
        for filename in os.listdir(latest_dir):
            if filename.endswith('.yaml'):
                src_file = os.path.join(latest_dir, filename)
                dst_file = os.path.join(version_dir, filename)
                
                with open(src_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Determine if this is installer or locale file
                is_locale_file = '.locale.' in filename
                is_installer_file = '.installer.' in filename
                
                # Update content with hashes and optionally release notes
                if is_locale_file and release_notes:
                    # Update locale file with release notes
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256, 
                        release_notes, release_notes_url, arch_hashes,
                        installer_urls, installer_url, product_codes
                    )
                elif is_installer_file and arch_hashes:
                    # Update installer file with multi-arch hashes and product codes
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256,
                        None, None, arch_hashes,
                        installer_urls, installer_url, product_codes
                    )
                    # Add missing architectures (e.g., arm64 if not in old version)
                    if installer_urls:
                        updated_content = add_missing_architectures(
                            updated_content, arch_hashes, installer_urls
                        )
                else:
                    # Update other files without release notes or multi-arch
                    updated_content = update_manifest_content(
                        content, version, sha256, signature_sha256,
                        None, None, arch_hashes,
                        installer_urls, installer_url, product_codes
                    )
                
                with open(dst_file, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                
                # Validate YAML after writing
                print(f"Updated: {filename}")
                if not validate_yaml_content(updated_content, filename):
                    print(f"  ⚠️  Warning: {filename} may have validation issues")
        
        return True
        
    except Exception as e:
        print(f"Error processing template: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def update_manifests(
    repo_dir: str,
    manifest_path: str,
    package_id: str,
    version: str,
    installer_url: str,
    release_notes: Optional[str] = None,
    release_notes_url: Optional[str] = None,
    installer_urls: Optional[Dict[str, str]] = None
) -> bool:
    """Update manifest files in the cloned repository"""
    try:
        # Multi-architecture support
        if installer_urls:
            print(f"Multi-architecture package detected: {', '.join(installer_urls.keys())}")
            arch_hashes = {}
            product_codes = {}
            
            # Calculate hash for each architecture
            for arch, url in installer_urls.items():
                print(f"\n📥 Processing {arch} architecture...")
                # Determine file extension
                if url.lower().endswith('.msi'):
                    file_ext = '.msi'
                    is_msi = True
                elif url.lower().endswith('.msix'):
                    file_ext = '.msix'
                    is_msi = False
                elif url.lower().endswith('.zip'):
                    file_ext = '.zip'
                    is_msi = False
                else:
                    file_ext = '.exe'
                    is_msi = False
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    tmp_path = tmp_file.name
                
                try:
                    if not download_file(url, tmp_path):
                        print(f"❌ Failed to download {arch} installer")
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                        continue
                    
                    # Calculate SHA256
                    arch_hash = calculate_sha256(tmp_path)
                    arch_hashes[arch] = arch_hash
                    print(f"  ✅ {arch} SHA256: {arch_hash}")
                    
                    # Extract ProductCode from MSI files
                    if is_msi:
                        product_code = extract_product_code_from_msi(tmp_path)
                        if product_code:
                            product_codes[arch] = product_code
                
                except Exception as e:
                    print(f"❌ Error processing {arch} installer: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                    # Always cleanup temp file
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
            
            if not arch_hashes:
                print("Failed to calculate hashes for any architecture")
                return False
            
            # Use first architecture as primary for backward compatibility
            sha256 = list(arch_hashes.values())[0]
            signature_sha256 = None
        else:
            # Single architecture (legacy)
            # Determine file extension from URL
            if installer_url.lower().endswith('.msi'):
                file_ext = '.msi'
                is_msi = True
                is_msix = False
            elif installer_url.lower().endswith('.msix'):
                file_ext = '.msix'
                is_msi = False
                is_msix = True
            else:
                file_ext = '.exe'
                is_msi = False
                is_msix = False
            
            # Download installer to calculate SHA256
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                tmp_path = tmp_file.name
            
            try:
                if not download_file(installer_url, tmp_path):
                    print("❌ Failed to download installer")
                    return False
                
                sha256 = calculate_sha256(tmp_path)
                print(f"✅ Calculated InstallerSha256: {sha256}")
                
                # Calculate SignatureSha256 for MSIX packages
                signature_sha256 = None
                if is_msix:
                    print("MSIX package detected, calculating SignatureSha256...")
                    signature_sha256 = calculate_msix_signature_sha256(tmp_path)
                
                # Extract ProductCode from MSI files
                product_codes = None
                if is_msi:
                    product_code = extract_product_code_from_msi(tmp_path)
                    if product_code:
                        product_codes = {'default': product_code}
                
            except Exception as e:
                print(f"❌ Error processing installer: {e}")
                import traceback
                traceback.print_exc()
                return False
            finally:
                # Always cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            
            arch_hashes = None
        
        # Update manifest files
        version_dir = os.path.join(repo_dir, manifest_path, version)
        
        # Check if version already exists
        if os.path.exists(version_dir):
            print(f"Version {version} already exists in repository")
            return False
        
        # Find latest version directory
        manifest_base = os.path.join(repo_dir, manifest_path)
        if not os.path.exists(manifest_base):
            print(f"Manifest path not found: {manifest_base}")
            return False
        
        versions = [d for d in os.listdir(manifest_base) if os.path.isdir(os.path.join(manifest_base, d))]
        if not versions:
            # Try to use template from specific commit if available
            config_file = None
            for f in ['manifests/*.checkver.yaml', 'manifests/**/*.checkver.yaml']:
                import glob
                matches = glob.glob(f)
                for match in matches:
                    with open(match, 'r') as cf:
                        checkver = yaml.safe_load(cf)
                        if checkver.get('packageIdentifier') == package_id:
                            config_file = match
                            break
                if config_file:
                    break
            
            if config_file:
                with open(config_file, 'r') as f:
                    checkver_config = yaml.safe_load(f)
                
                template_commit = checkver_config.get('templateCommit')
                template_version = checkver_config.get('templateVersion')
                
                if template_commit and template_version:
                    print(f"No existing versions found on master branch")
                    print(f"Using template version {template_version} from commit {template_commit}")
                    
                    # Fetch manifest from specific commit to TEMPORARY directory (outside repo)
                    # This ensures template files are NOT committed to Git
                    with tempfile.TemporaryDirectory() as temp_template_dir:
                        template_dir = os.path.join(temp_template_dir, template_version)
                        os.makedirs(template_dir, exist_ok=True)
                        
                        # Fetch all yaml files from the template commit
                        api_url = f"https://api.github.com/repos/microsoft/winget-pkgs/contents/{manifest_path}/{template_version}?ref={template_commit}"
                        try:
                            response = requests.get(api_url, timeout=30)
                            response.raise_for_status()
                            files = response.json()
                            
                            for file_info in files:
                                if file_info['name'].endswith('.yaml'):
                                    file_content = fetch_github_file(
                                        'microsoft/winget-pkgs',
                                        f"{manifest_path}/{template_version}/{file_info['name']}",
                                        template_commit
                                    )
                                    if file_content:
                                        with open(os.path.join(template_dir, file_info['name']), 'w', encoding='utf-8') as f:
                                            f.write(file_content)
                                        print(f"  Downloaded template: {file_info['name']}")
                            
                            versions = [template_version]
                            latest_version = template_version
                            latest_dir = template_dir
                            print(f"✅ Template version {template_version} fetched successfully")
                            print(f"   (Template stored in temporary directory, will not be committed)")
                            
                            # Process the template immediately within this context
                            # so latest_dir remains valid
                            return process_template_and_create_version(
                                repo_dir, manifest_path, version, latest_dir, latest_version,
                                sha256, signature_sha256, release_notes, release_notes_url,
                                arch_hashes, installer_urls, installer_url, product_codes
                            )
                        except Exception as e:
                            print(f"Error fetching template from commit {template_commit}: {e}")
                            return False
                else:
                    print("No existing versions found")
                    return False
            else:
                print("No existing versions found")
                return False
        else:
            # Sort versions and get latest (only if we didn't already set it from template)
            # Use a robust sorting key that handles:
            # - Numeric versions: 1.2.3
            # - Date-based versions with dots: 2025.10.13
            # - Date-based versions with hyphens: 2025-09-16
            def version_sort_key(v):
                parts = []
                # Split by both dots and hyphens to handle all formats
                for x in re.split(r'[.\-]', v):
                    try:
                        # Try to convert to int for numeric comparison
                        parts.append(int(x))
                    except ValueError:
                        # If it contains non-numeric characters, treat as 0
                        # This ensures consistent type (all ints)
                        parts.append(0)
                return parts
            
            versions.sort(key=version_sort_key)
            latest_version = versions[-1]
            latest_dir = os.path.join(manifest_base, latest_version)
            
            print(f"Available versions in repository: {', '.join(versions[-5:])}")  # Show last 5
            print(f"Selected latest version: {latest_version}")
            
            # Sanity check: warn if selected version is newer than target version
            if version_sort_key(latest_version) >= version_sort_key(version):
                print(f"⚠️  WARNING: Latest version {latest_version} >= target version {version}")
                print(f"   This might indicate the version already exists or there's a versioning issue")
            
            # Process template from repo directory (normal case)
            return process_template_and_create_version(
                repo_dir, manifest_path, version, latest_dir, latest_version,
                sha256, signature_sha256, release_notes, release_notes_url,
                arch_hashes, installer_urls, installer_url, product_codes
            )
        
    except Exception as e:
        print(f"Error updating manifests: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def commit_and_push(repo_dir: str, package_id: str, version: str, branch_name: str, token: str) -> bool:
    """Commit changes and push to fork"""
    try:
        # Add changes
        subprocess.run(
            ['git', 'add', '.'],
            cwd=repo_dir,
            check=True
        )
        
        # Commit
        commit_msg = f"New version: {package_id} version {version}"
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=repo_dir,
            check=True
        )
        
        # Get remote URL with token
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        remote_url = result.stdout.strip()
        
        # Update remote URL with token if not already present
        if token not in remote_url and not remote_url.startswith('https://'):
            # Assume it's SSH, convert to HTTPS with token
            if remote_url.startswith('git@github.com:'):
                repo_path = remote_url.replace('git@github.com:', '').replace('.git', '')
                remote_url = f"https://{token}@github.com/{repo_path}.git"
                subprocess.run(
                    ['git', 'remote', 'set-url', 'origin', remote_url],
                    cwd=repo_dir,
                    check=True
                )
        
        # Push
        subprocess.run(
            ['git', 'push', 'origin', branch_name],
            cwd=repo_dir,
            check=True
        )
        
        return True
    except Exception as e:
        print(f"Error committing/pushing: {e}", file=sys.stderr)
        return False


def create_pull_request(
    fork_owner: str,
    package_id: str,
    version: str,
    branch_name: str,
    workflow_run_number: str,
    workflow_run_id: str,
    repo_name: str = "winget-pkgs-updater"
) -> bool:
    """Create pull request using GitHub CLI"""
    try:
        title = f"New version: {package_id} version {version}"
        print(f"Creating PR: {title}")
        
        # Build PR body with separate links for repo and workflow run
        repo_url = f"https://github.com/{fork_owner}/{repo_name}"
        workflow_url = f"https://github.com/{fork_owner}/{repo_name}/actions/runs/{workflow_run_id}"
        body = f"Automated by [{fork_owner}/{repo_name}]({repo_url}) in workflow run [#{workflow_run_number}]({workflow_url})."
        
        # Use gh CLI to create PR
        subprocess.run(
            [
                'gh', 'pr', 'create',
                '--repo', 'microsoft/winget-pkgs',
                '--title', title,
                '--body', body,
                '--head', f"{fork_owner}:{branch_name}"
            ],
            check=True
        )
        
        print(f"✅ Pull request created: {title}")
        print(f"📝 Workflow run: {workflow_url}")
        return True
        
    except Exception as e:
        print(f"Error creating PR: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Update WinGet manifest with new version'
    )
    parser.add_argument('checkver_config', help='Path to checkver config file')
    parser.add_argument('version_info', help='Path to version info JSON file')
    parser.add_argument('--no-pr', action='store_true',
                        help='Update manifests without creating PR (for testing)')
    parser.add_argument('--fork-path', help='Path to existing fork clone (for testing)')
    
    args = parser.parse_args()
    
    # Load version info from check_version.py output
    with open(args.version_info, 'r') as f:
        version_info = json.load(f)
    
    package_id = version_info['packageIdentifier']
    version = version_info['version']
    installer_url = version_info['installerUrl']
    checkver_config = version_info['checkver_config']
    manifest_path = checkver_config.get('manifestPath', '')
    
    # Get multi-architecture URLs if available
    installer_urls = version_info.get('installerUrls')
    
    # Get release notes if available
    release_notes = version_info.get('releaseNotes')
    release_notes_url = version_info.get('releaseNotesUrl')
    
    print(f"Updating {package_id} to version {version}")
    
    if installer_urls:
        print(f"Multi-architecture package: {', '.join(installer_urls.keys())}")
    
    if release_notes:
        print(f"📝 Release notes available ({len(release_notes)} chars)")
    
    # Check if PR already exists BEFORE doing any work (skip if --no-pr)
    if not args.no_pr and check_existing_pr(package_id, version):
        print("⏭️  Skipping update - PR already exists")
        sys.exit(0)  # Exit successfully - no work needed
    
    # Get environment variables
    fork_repo = os.getenv('WINGET_FORK_REPO')
    if not fork_repo:
        fork_owner = os.getenv('GITHUB_REPOSITORY_OWNER', 'zeldrisho')
        fork_repo = f"{fork_owner}/winget-pkgs"
    
    workflow_run_number = os.getenv('GITHUB_RUN_NUMBER', 'unknown')
    workflow_run_id = os.getenv('GITHUB_RUN_ID', 'unknown')
    repo_name = os.getenv('GITHUB_REPOSITORY', 'zeldrisho/winget-pkgs-updater').split('/')[-1]
    token = os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    
    if not token:
        print("Error: GITHUB_TOKEN or GH_TOKEN environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Extract fork_owner from fork_repo for PR creation
    fork_owner = fork_repo.split('/')[0]
    
    # Use provided fork path or create temporary directory
    if args.fork_path:
        # Use existing fork clone
        repo_dir = args.fork_path
        print(f"Using existing fork at: {repo_dir}")
        
        # Update manifests with release notes and multi-arch support
        if not update_manifests(repo_dir, manifest_path, package_id, version, installer_url, release_notes, release_notes_url, installer_urls):
            print("Failed to update manifests")
            sys.exit(1)
        
        print(f"✅ Successfully updated manifests in {repo_dir}")
    else:
        # Create temporary directory for cloning (original workflow)
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_dir = os.path.join(temp_dir, 'winget-pkgs')
            
            # Clone fork
            if not clone_winget_pkgs(fork_repo, repo_dir, token):
                print("Failed to clone repository")
                sys.exit(1)
            
            # Create branch
            branch_name = create_pr_branch(repo_dir, package_id, version)
            print(f"Created branch: {branch_name}")
            
            # Update manifests with release notes and multi-arch support
            if not update_manifests(repo_dir, manifest_path, package_id, version, installer_url, release_notes, release_notes_url, installer_urls):
                print("Failed to update manifests")
                sys.exit(1)
            
            # Commit and push
            if not commit_and_push(repo_dir, package_id, version, branch_name, token):
                print("Failed to commit/push changes")
                sys.exit(1)
            
            # Create PR (skip if --no-pr)
            if not args.no_pr:
                if not create_pull_request(fork_owner, package_id, version, branch_name, workflow_run_number, workflow_run_id, repo_name):
                    print("Failed to create pull request")
                    sys.exit(1)
                
                print(f"✅ Successfully created PR for {package_id} version {version}")
            else:
                print(f"✅ Successfully updated manifests for {package_id} version {version} (no PR created)")



if __name__ == '__main__':
    main()
