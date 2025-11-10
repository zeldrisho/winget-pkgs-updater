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
        # Try gh CLI first, fallback to HTTP API
        try:
            result = subprocess.run(
                ['gh', 'api', f'/repos/microsoft/winget-pkgs/contents/{path}'],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True
        except (FileNotFoundError, OSError):
            # gh CLI not available, will use HTTP API
            pass
        
        # Fallback to HTTP API
        import requests
        url = f"https://api.github.com/repos/microsoft/winget-pkgs/contents/{path}"
        response = requests.get(url, timeout=30)
        return response.status_code == 200
        
    except Exception:
        return False


def derive_manifest_path(package_id: str) -> str:
    """
    Derive manifest path from package identifier with intelligent detection.
    
    Handles various path patterns:
    - Standard: Microsoft.PowerShell -> manifests/m/Microsoft/PowerShell
    - Version subdirectory: RoyalApps.RoyalTS.7 -> manifests/r/RoyalApps/RoyalTS/7
    - Deep nesting: Microsoft.VisualStudio.2022.Community -> manifests/m/Microsoft/VisualStudio/2022/Community
    
    The function will check multiple path patterns by querying GitHub:
    1. Standard path (all after first dot as package name)
    2. Deep nested paths (each dot creates a subdirectory)
    3. Version subdirectory patterns (last segment is a number)
    """
    # Split by first dot to get publisher
    parts = package_id.split('.', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid package identifier format: {package_id}")
    
    publisher, remaining = parts
    first_letter = publisher[0].lower()
    
    # Try different path patterns in order of likelihood
    all_parts = package_id.split('.')
    
    # Pattern 1: Deep nested path (each part becomes a directory)
    # Microsoft.VisualStudio.2022.Community -> manifests/m/Microsoft/VisualStudio/2022/Community
    deep_path = f"manifests/{first_letter}/{'/'.join(all_parts)}"
    
    # Pattern 2: Standard path (Publisher/RestOfPackageId)
    # Microsoft.PowerShell -> manifests/m/Microsoft/PowerShell
    standard_path = f"manifests/{first_letter}/{publisher}/{remaining}"
    
    # Pattern 3: Version subdirectory (Publisher/Package/Version)
    # RoyalApps.RoyalTS.7 -> manifests/r/RoyalApps/RoyalTS/7
    remaining_parts = remaining.split('.')
    versioned_path = None
    if len(remaining_parts) >= 2 and remaining_parts[-1].isdigit():
        package_name = '.'.join(remaining_parts[:-1])
        version_dir = remaining_parts[-1]
        versioned_path = f"manifests/{first_letter}/{publisher}/{package_name}/{version_dir}"
    
    # Check paths in order: deep nested -> versioned -> standard
    paths_to_check = [
        ("deep nested", deep_path),
        ("versioned", versioned_path) if versioned_path else None,
        ("standard", standard_path)
    ]
    paths_to_check = [p for p in paths_to_check if p is not None]
    
    print(f"Detecting manifest path pattern for {package_id}...", flush=True)
    for path_type, path in paths_to_check:
        if check_path_exists_on_github(path):
            print(f"  ✓ Found {path_type} path: {path}", flush=True)
            return path
    
    # If nothing exists, prefer deep nested for packages with 3+ parts
    # (like Microsoft.VisualStudio.2022.Community), otherwise use standard
    if len(all_parts) > 2:
        print(f"  ⚠ Path doesn't exist yet, using deep nested path for new package", flush=True)
        return deep_path
    else:
        print(f"  ⚠ Path doesn't exist yet, using standard path for new package", flush=True)
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


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python config.py get-manifest-path <package_identifier>", file=sys.stderr)
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'get-manifest-path':
        package_id = sys.argv[2]
        try:
            manifest_path = derive_manifest_path(package_id)
            print(manifest_path)
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)
