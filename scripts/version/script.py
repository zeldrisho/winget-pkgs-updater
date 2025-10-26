"""
Script-based version checking using PowerShell
"""

import re
import sys
import subprocess
from typing import Optional, Dict, Tuple


def normalize_version(version: str) -> str:
    """
    Normalize version string by removing unnecessary leading zeros in version parts.
    
    Examples:
    - "7.03.51009.0" -> "7.3.51009.0"
    - "1.02.3.04" -> "1.2.3.4"
    - "10.01.100.001" -> "10.1.100.1"
    - "1.0.0.0" -> "1.0.0.0" (trailing zeros are kept)
    
    This handles cases where upstream uses formats like "7.03" but WinGet uses "7.3"
    """
    parts = version.split('.')
    normalized_parts = []
    
    for part in parts:
        # Remove leading zeros but keep at least one digit
        # "03" -> "3", "003" -> "3", "0" -> "0", "100" -> "100"
        normalized = str(int(part))
        normalized_parts.append(normalized)
    
    return '.'.join(normalized_parts)


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


def get_latest_version_script(checkver_config: Dict) -> Optional[Tuple[str, Dict]]:
    r"""
    Extract version using PowerShell script method.
    Returns tuple of (version, metadata_dict) where metadata contains
    named groups from regex match for use in URL templates.
    
    Supports optional 'replace' field for transforming matched version string.
    Example: regex "(\d{2})/(\d{2})/(\d{4})" with replace "${3}.${1}.${2}"
    transforms "10/13/2025" to "2025.10.13"
    """
    try:
        checkver = checkver_config.get('checkver', {})
        
        # Check if this uses script-based checkver
        if checkver.get('type') != 'script':
            return None
            
        script = checkver.get('script', '')
        regex_pattern = checkver.get('regex', '')
        replace_pattern = checkver.get('replace', '')
        
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
            # If replace pattern is provided, use it to transform the version
            if replace_pattern:
                # Replace ${1}, ${2}, etc. with corresponding capture groups
                version = replace_pattern
                for i, group in enumerate(match.groups(), start=1):
                    version = version.replace(f"${{{i}}}", group)
                print(f"Applied replace pattern: {version}")
            else:
                # Default: use first capture group
                version = match.group(1)
            
            print(f"Extracted version: {version}")
            
            # Store original version format for URL templates
            # Some URLs require the original format (e.g., "7.03" instead of "7.3")
            original_version = version
            
            # Normalize version to remove leading zeros in parts
            # e.g., "7.03.51009.0" -> "7.3.51009.0"
            normalized_version = normalize_version(version)
            if normalized_version != version:
                print(f"Normalized version: {normalized_version}")
                version = normalized_version
            
            # Extract all named groups as metadata
            # This allows custom placeholders like {rcversion}, {build}, etc.
            metadata = match.groupdict()
            
            # Add original version to metadata for URL templates that need it
            if original_version != version:
                metadata['versionOriginal'] = original_version
                print(f"Added versionOriginal to metadata: {original_version}")
            
            if metadata:
                print(f"Extracted metadata: {metadata}")
            
            return (version, metadata)
        else:
            print(f"Regex pattern '{regex_pattern}' did not match output")
            return None
            
    except Exception as e:
        print(f"Error in script-based version check: {e}", file=sys.stderr)
        return None
