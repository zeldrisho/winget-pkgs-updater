"""
Configuration loader for checkver YAML files
"""

import os
import yaml
import subprocess
import json
from typing import Dict, Optional


def derive_package_identifier(checkver_path: str) -> str:
    """
    Derive package identifier from checkver filename.
    Example: Microsoft.PowerShell.checkver.yaml -> Microsoft.PowerShell
    """
    filename = os.path.basename(checkver_path)
    # Remove .checkver.yaml extension
    package_id = filename.replace('.checkver.yaml', '')
    return package_id


def check_path_exists_on_github(path: str) -> bool:
    """
    Check if a path exists in microsoft/winget-pkgs repository.
    Returns True if the path exists, False otherwise.
    """
    try:
        result = subprocess.run(
            ['gh', 'api', f'/repos/microsoft/winget-pkgs/contents/{path}'],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def derive_manifest_path(package_id: str) -> str:
    """
    Derive manifest path from package identifier with intelligent detection.
    
    Handles special cases like:
    - Standard: Microsoft.PowerShell -> manifests/m/Microsoft/PowerShell
    - Version subdirectory: RoyalApps.RoyalTS.7 -> manifests/r/RoyalApps/RoyalTS/7
    
    The function will check if the package has version subdirectories by:
    1. First trying the standard path (treating last part as package name)
    2. If not found, check if it's a version subdirectory pattern (ends with digit)
    3. Try alternative path structure
    """
    # Split by first dot to get publisher and remaining parts
    parts = package_id.split('.', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid package identifier format: {package_id}")
    
    publisher, remaining = parts
    first_letter = publisher[0].lower()
    
    # Standard path: treat entire remaining as package name
    standard_path = f"manifests/{first_letter}/{publisher}/{remaining}"
    
    # Check if the last segment looks like a version number (ends with digit)
    # and there are at least 2 more dots (Publisher.Package.Version)
    remaining_parts = remaining.split('.')
    if len(remaining_parts) >= 2 and remaining_parts[-1].isdigit():
        # Potential version subdirectory pattern
        # e.g., RoyalApps.RoyalTS.7 -> try manifests/r/RoyalApps/RoyalTS/7
        package_name = '.'.join(remaining_parts[:-1])
        version_dir = remaining_parts[-1]
        versioned_path = f"manifests/{first_letter}/{publisher}/{package_name}/{version_dir}"
        
        # Check which path exists on GitHub
        print(f"Checking for version subdirectory pattern...", flush=True)
        if check_path_exists_on_github(versioned_path):
            print(f"  ✓ Found versioned path: {versioned_path}", flush=True)
            return versioned_path
        elif check_path_exists_on_github(standard_path):
            print(f"  ✓ Found standard path: {standard_path}", flush=True)
            return standard_path
        else:
            # Default to versioned path if neither exists (for new packages)
            print(f"  ⚠ Neither path exists, using versioned path for new package", flush=True)
            return versioned_path
    
    # Standard case: no version subdirectory
    return standard_path


def load_checkver_config(checkver_path: str) -> Dict:
    """
    Load checkver configuration from YAML file.
    Automatically derives packageIdentifier and manifestPath if not present.
    """
    with open(checkver_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Auto-derive packageIdentifier from filename if not present
    if 'packageIdentifier' not in config:
        config['packageIdentifier'] = derive_package_identifier(checkver_path)
    
    # Auto-derive manifestPath from packageIdentifier if not present
    if 'manifestPath' not in config:
        config['manifestPath'] = derive_manifest_path(config['packageIdentifier'])
    
    return config
