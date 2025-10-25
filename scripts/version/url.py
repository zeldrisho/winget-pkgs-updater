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
    - Any named group from regex metadata (e.g., {rcversion}, {build})
    """
    template = checkver_config.get('installerUrlTemplate', '')
    
    if not metadata:
        metadata = {}
    
    # Handle versionShort placeholder (e.g., 2.3.12.0 -> 2.3.12)
    version_short = re.sub(r'\.0$', '', version)
    
    # Build replacement dict with version, versionShort, and all metadata
    replacements = {
        'version': version,
        'versionShort': version_short,
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
    """
    # First try to get from metadata (extracted from script output)
    release_notes = metadata.get('releasenotes') if metadata else None
    release_notes_url = metadata.get('releasenotesurl') if metadata else None
    
    # Fallback to checkver config
    if not release_notes:
        release_notes = checkver_config.get('releaseNotes')
    if not release_notes_url:
        release_notes_url = checkver_config.get('releaseNotesUrl')
    
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
