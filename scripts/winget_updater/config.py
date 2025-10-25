"""
Configuration loader for checkver YAML files
"""

import yaml
from typing import Dict


def load_checkver_config(checkver_path: str) -> Dict:
    """Load checkver configuration from YAML file"""
    with open(checkver_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)
