#!/usr/bin/env python3
"""
Utility functions for version comparison and sorting.
Uses packaging.version for robust semantic version handling.
"""

from typing import List
from packaging import version


def get_latest_version(versions: List[str]) -> str:
    """
    Get the latest version from a list of version strings.
    Uses semantic versioning comparison to handle various formats correctly.
    
    Args:
        versions: List of version strings (e.g., ["1.2.3", "1.2.4-beta", "1.2.4"])
        
    Returns:
        The latest version string
        
    Raises:
        ValueError: If versions list is empty
    """
    if not versions:
        raise ValueError("Cannot get latest version from empty list")
    
    # Parse all versions and keep track of original strings
    parsed_versions = []
    for v in versions:
        try:
            parsed_versions.append((version.parse(v), v))
        except Exception as e:
            # If parsing fails, try to sanitize the version
            # Replace common separators with dots
            sanitized = v.replace('-', '.').replace('_', '.')
            try:
                parsed_versions.append((version.parse(sanitized), v))
            except Exception:
                # Last resort: use the original string but it will sort poorly
                print(f"Warning: Could not parse version '{v}', may be sorted incorrectly")
                # Create a fallback version that will sort low
                parsed_versions.append((version.parse("0.0.0"), v))
    
    # Sort by parsed version and return the original string of the highest version
    parsed_versions.sort(key=lambda x: x[0])
    return parsed_versions[-1][1]


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two version strings.
    
    Args:
        v1: First version string
        v2: Second version string
        
    Returns:
        -1 if v1 < v2
         0 if v1 == v2
         1 if v1 > v2
    """
    try:
        pv1 = version.parse(v1)
        pv2 = version.parse(v2)
        
        if pv1 < pv2:
            return -1
        elif pv1 > pv2:
            return 1
        else:
            return 0
    except Exception as e:
        print(f"Warning: Could not compare versions '{v1}' and '{v2}': {e}")
        # Fallback to string comparison
        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0


def is_newer_version(current: str, new: str) -> bool:
    """
    Check if new version is newer than current version.
    
    Args:
        current: Current version string
        new: New version string
        
    Returns:
        True if new version is newer than current
    """
    return compare_versions(new, current) > 0
