"""
Script-based version checking using PowerShell
"""

import re
import sys
import subprocess
from typing import Optional, Dict, Tuple


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
            
            # Extract all named groups as metadata
            # This allows custom placeholders like {rcversion}, {build}, etc.
            metadata = match.groupdict()
            if metadata:
                print(f"Extracted metadata: {metadata}")
            
            return (version, metadata)
        else:
            print(f"Regex pattern '{regex_pattern}' did not match output")
            return None
            
    except Exception as e:
        print(f"Error in script-based version check: {e}", file=sys.stderr)
        return None
