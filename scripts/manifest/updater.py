"""
Manifest content update logic
"""

import re
from datetime import datetime
from typing import Optional, Dict

from yaml_utils import remove_duplicate_fields


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
    """
    
    # Extract old version from PackageVersion field
    old_version = None
    version_match = re.search(r'PackageVersion:\s*([\d\.]+)', content)
    if version_match:
        old_version = version_match.group(1)
        print(f"  Detected old version: {old_version}")
        print(f"  Updating to new version: {version}")
    
    # Replace ALL occurrences of old version with new version
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
        content = _update_multi_arch_urls(content, installer_urls)
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
        content = _update_multi_arch_hashes(content, arch_hashes)
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
        content = _update_product_codes(content, product_codes)
    
    # Update ReleaseDate to today (ISO 8601 format: YYYY-MM-DD)
    today = datetime.now().strftime('%Y-%m-%d')
    if re.search(r'ReleaseDate:\s*[\d-]+', content):
        count = [0]
        def replace_release_date(match):
            count[0] += 1
            if count[0] == 1:
                return f'ReleaseDate: {today}'
            else:
                print(f"  ⚠️  Removed duplicate ReleaseDate (occurrence #{count[0]})")
                return ''
        
        content = re.sub(r'ReleaseDate:\s*[\d-]+', replace_release_date, content)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        if count[0] > 0:
            print(f"  ✅ Updated ReleaseDate to {today}")
            if count[0] > 1:
                print(f"     (Removed {count[0] - 1} duplicate(s))")
    
    # Update ReleaseNotes if provided
    if release_notes and re.search(r'ReleaseNotes:', content):
        content = _update_release_notes(content, release_notes)
    
    # Update ReleaseNotesUrl if provided
    if release_notes_url and re.search(r'ReleaseNotesUrl:', content):
        content = _update_release_notes_url(content, release_notes_url)
    
    # Final cleanup: Remove any remaining duplicate fields
    content = remove_duplicate_fields(content)
    
    return content


def _update_multi_arch_urls(content: str, installer_urls: Dict[str, str]) -> str:
    """Update URLs for multi-architecture packages"""
    lines = content.split('\n')
    updated_lines = []
    current_arch = None
    updated_archs = set()
    
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
                print(f"  ⚠️  Removed duplicate InstallerUrl for {current_arch}")
                continue
        
        updated_lines.append(line)
    
    content = '\n'.join(updated_lines)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    return content


def _update_multi_arch_hashes(content: str, arch_hashes: Dict[str, str]) -> str:
    """Update SHA256 hashes for multi-architecture packages"""
    lines = content.split('\n')
    updated_lines = []
    current_arch = None
    updated_archs = set()
    
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
                print(f"  ⚠️  Removed duplicate InstallerSha256 for {current_arch}")
                continue
        
        updated_lines.append(line)
    
    content = '\n'.join(updated_lines)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    return content


def _update_product_codes(content: str, product_codes: Dict[str, str]) -> str:
    """Update ProductCode for multi-architecture and AppsAndFeaturesEntries"""
    lines = content.split('\n')
    updated_lines = []
    current_arch = None
    in_apps_features = False
    in_installers_section = False
    updated_contexts = set()
    
    for line in lines:
        # Track sections
        if 'Installers:' in line and line.strip() == 'Installers:':
            in_installers_section = True
            in_apps_features = False
        
        if in_installers_section and re.match(r'^\s*-\s*Architecture:\s*(\w+)', line):
            match = re.match(r'^\s*-\s*Architecture:\s*(\w+)', line)
            current_arch = match.group(1)
        
        if 'AppsAndFeaturesEntries:' in line:
            in_apps_features = True
            in_installers_section = False
            current_arch = None
        elif line and not line.startswith(' ') and not line.startswith('-'):
            if not line.strip().startswith('#'):
                in_apps_features = False
                in_installers_section = False
        
        # Update ProductCode in different contexts
        if 'ProductCode:' in line:
            indent = len(line) - len(line.lstrip())
            context_key = None
            should_update = False
            
            if in_apps_features and 'default' in product_codes:
                context_key = 'apps_features'
                if context_key not in updated_contexts:
                    line = ' ' * indent + f"- ProductCode: '{product_codes['default']}'"
                    print(f"  ✅ Updated ProductCode in AppsAndFeaturesEntries")
                    should_update = True
                else:
                    print(f"  ⚠️  Removed duplicate ProductCode in AppsAndFeaturesEntries")
                    continue
            elif in_installers_section and current_arch and current_arch in product_codes:
                context_key = f'installer_{current_arch}'
                if context_key not in updated_contexts:
                    line = ' ' * indent + f"ProductCode: '{product_codes[current_arch]}'"
                    print(f"  ✅ Updated {current_arch} ProductCode in Installers")
                    should_update = True
                else:
                    print(f"  ⚠️  Removed duplicate ProductCode for {current_arch} in Installers")
                    continue
            elif not in_apps_features and not in_installers_section and 'default' in product_codes:
                context_key = 'top_level'
                if context_key not in updated_contexts:
                    line = ' ' * indent + f"ProductCode: '{product_codes['default']}'"
                    print(f"  ✅ Updated top-level ProductCode")
                    should_update = True
                else:
                    print(f"  ⚠️  Removed duplicate top-level ProductCode")
                    continue
            
            if should_update and context_key:
                updated_contexts.add(context_key)
        
        updated_lines.append(line)
    
    return '\n'.join(updated_lines)


def _update_release_notes(content: str, release_notes: str) -> str:
    """Update ReleaseNotes field in manifest"""
    yaml_notes = release_notes.replace('\r\n', '\n').replace('\r', '\n')
    
    if re.search(r'ReleaseNotes:\s*\|-', content):
        # Block scalar format
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
        # Single line format
        count = [0]
        def replace_notes_line(match):
            count[0] += 1
            if count[0] == 1:
                return f'ReleaseNotes: |-\n  {yaml_notes.replace(chr(10), chr(10) + "  ")}'
            else:
                print(f"  ⚠️  Removed duplicate ReleaseNotes (occurrence #{count[0]})")
                return ''
        
        content = re.sub(r'(ReleaseNotes:).*', replace_notes_line, content)
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        if count[0] > 0:
            print(f"  ✅ Updated ReleaseNotes")
    
    return content


def _update_release_notes_url(content: str, release_notes_url: str) -> str:
    """Update ReleaseNotesUrl field in manifest"""
    count = [0]
    def replace_notes_url(match):
        count[0] += 1
        if count[0] == 1:
            return f'ReleaseNotesUrl: {release_notes_url}'
        else:
            print(f"  ⚠️  Removed duplicate ReleaseNotesUrl (occurrence #{count[0]})")
            return ''
    
    content = re.sub(r'ReleaseNotesUrl:.*', replace_notes_url, content)
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    if count[0] > 0:
        print(f"  ✅ Updated ReleaseNotesUrl")
    
    return content


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
    
    # Extract the structure from the last installer
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
    for arch in sorted(new_archs):
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
