"""
Configuration loader for checkver YAML files
"""

import os
import yaml
from typing import Dict


def derive_package_identifier(checkver_path: str) -> str:
    """
    Derive package identifier from checkver filename.
    Example: Microsoft.PowerShell.checkver.yaml -> Microsoft.PowerShell
    """
    filename = os.path.basename(checkver_path)
    # Remove .checkver.yaml extension
    package_id = filename.replace('.checkver.yaml', '')
    return package_id


def derive_manifest_path(package_id: str) -> str:
    """
    Derive manifest path from package identifier.
    Example: Microsoft.PowerShell -> manifests/m/Microsoft/PowerShell
    Example: Seelen.SeelenUI -> manifests/s/Seelen/SeelenUI
    """
    # Split by first dot to get publisher and package
    parts = package_id.split('.', 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid package identifier format: {package_id}")
    
    publisher, package = parts
    first_letter = publisher[0].lower()
    
    return f"manifests/{first_letter}/{publisher}/{package}"


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
