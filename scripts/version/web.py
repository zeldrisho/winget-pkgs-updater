"""
Web-based version checking (legacy support)
"""

import re
import sys
import requests
from typing import Optional


def get_latest_version_from_web(check_url: str) -> Optional[str]:
    """Extract version from web page"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(check_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Look for version patterns in the HTML
        # Common patterns: v1.2.3, 1.2.3, version 1.2.3
        patterns = [
            r'Zalo-(\d+\.\d+\.\d+)-win64\.msi',
            r'version["\s:]+(\d+\.\d+\.\d+)',
            r'v(\d+\.\d+\.\d+)',
            r'(\d+\.\d+\.\d+)',
        ]
        
        content = response.text
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Return the first match that looks like a valid version
                version = matches[0]
                if re.match(r'^\d+\.\d+\.\d+$', version):
                    return version
        
        return None
    except Exception as e:
        print(f"Error fetching version from {check_url}: {e}", file=sys.stderr)
        return None
