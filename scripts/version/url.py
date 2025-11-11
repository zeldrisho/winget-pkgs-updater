"""
URL template handling and installer verification
"""

import re
import requests
from typing import Dict


def get_installer_url(checkver_config: Dict, version: str, metadata: Dict = None) -> str:
    """
    Generate installer URL from template.
    Supports placeholders:
    - {version}: Full version (e.g., 4.6.250531)
    - {versionShort}: Version without trailing .0 (e.g., 4.6.250531 -> 4.6.250531, 2.4.4.0 -> 2.4.4)
    - {versionNoDots}: Version with dots removed (e.g., 6.9.0.17160 -> 69017160)
    - {versionMajor}: Major version only (e.g., 3.0.0.36 -> 3)
    - {versionMajorMinor}: Major.Minor version (e.g., 9.5.0 -> 9.5)
    - Any named group from regex metadata (e.g., {rcversion}, {build})
    """
    template = checkver_config.get('installerUrlTemplate', '')
    
    if not metadata:
        metadata = {}
    
    # Handle versionShort placeholder (e.g., 2.3.12.0 -> 2.3.12)
    version_short = re.sub(r'\.0$', '', version)
    
    # Handle versionNoDots placeholder (e.g., 6.9.0.17160 -> 69017160)
    version_no_dots = version.replace('.', '')
    
    # Handle version component placeholders
    version_parts = version.split('.')
    version_major = version_parts[0] if len(version_parts) >= 1 else version
    version_major_minor = '.'.join(version_parts[:2]) if len(version_parts) >= 2 else version
    
    # Build replacement dict with version, versionShort, and all metadata
    replacements = {
        'version': version,
        'versionShort': version_short,
        'versionNoDots': version_no_dots,
        'versionMajor': version_major,
        'versionMajorMinor': version_major_minor,
        **metadata  # Include all custom metadata (rcversion, build, etc.)
    }
    
    return template.format(**replacements)


def verify_installer_exists(url: str) -> bool:
    """Verify that the installer URL is accessible"""
    try:
        response = requests.head(url, timeout=10, allow_redirects=True)
        return response.status_code == 200
    except Exception as e:
        print(f"Error verifying installer URL {url}: {e}")
        return False


def get_release_info_from_config(checkver_config: Dict, metadata: Dict) -> Dict:
    """
    Get release notes from checkver config or metadata if defined.
    Returns dict with releaseNotes and releaseNotesUrl, or None if not defined.
    Supports releaseNotesScript for dynamic fetching of release notes.
    """
    # First try to get from metadata (extracted from script output)
    release_notes = metadata.get('releasenotes') if metadata else None
    release_notes_url = metadata.get('releasenotesurl') if metadata else None
    
    # Fallback to checkver config
    if not release_notes:
        release_notes = checkver_config.get('releaseNotes')
    if not release_notes_url:
        release_notes_url = checkver_config.get('releaseNotesUrlTemplate')
    
    # Execute releaseNotesScript if defined and no release notes yet
    if not release_notes and 'releaseNotesScript' in checkver_config:
        release_notes_script = checkver_config['releaseNotesScript']
        if metadata and '{' in release_notes_script:
            # Replace metadata placeholders in script
            for key, value in metadata.items():
                release_notes_script = release_notes_script.replace('{' + key + '}', str(value))
        
        # Execute the PowerShell script
        from .script import run_powershell_script
        script_output = run_powershell_script(release_notes_script)
        if script_output and script_output.strip():
            release_notes = script_output.strip()
            print(f"✅ Fetched release notes from script ({len(release_notes)} chars)")
    
    if not release_notes and not release_notes_url:
        return None
    
    # Format with metadata placeholders if needed
    if release_notes_url and metadata and '{' in release_notes_url:
        release_notes_url = release_notes_url.format(**metadata)
    
    result = {}
    if release_notes:
        result['releaseNotes'] = release_notes
    if release_notes_url:
        result['releaseNotesUrl'] = release_notes_url
    
    if result:
        print(f"✅ Release info: {result}")
    return result if result else None
