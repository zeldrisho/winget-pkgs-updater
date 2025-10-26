"""
YAML validation
"""

import yaml


def validate_yaml_content(content: str, filepath: str = "manifest") -> bool:
    """
    Validate YAML content.
    Returns True if valid, False otherwise.
    """
    try:
        # Try to parse the YAML
        parsed = yaml.safe_load(content)
        return True
        
    except yaml.YAMLError as e:
        print(f"  ❌ YAML validation error in {filepath}: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Validation error in {filepath}: {e}")
        return False
