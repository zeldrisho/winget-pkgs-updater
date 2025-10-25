"""
MSI package ProductCode extraction using msitools
"""

import subprocess
from typing import Optional


def extract_product_code_from_msi(msi_path: str) -> Optional[str]:
    """
    Extract ProductCode from MSI file using msitools.
    Returns ProductCode in format {XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}
    Returns None if extraction fails.
    """
    try:
        # Use msiinfo to extract Property table from MSI
        result = subprocess.run(
            ['msiinfo', 'export', msi_path, 'Property'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout:
            # Parse output to find ProductCode
            # Format: ProductCode\t{GUID}
            for line in result.stdout.split('\n'):
                if line.startswith('ProductCode'):
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        product_code = parts[1].strip()
                        print(f"  Extracted ProductCode: {product_code}")
                        return product_code
        else:
            print(f"  Warning: Could not extract ProductCode: {result.stderr}")
            return None
            
    except FileNotFoundError:
        print("  Warning: msitools not installed. Cannot extract ProductCode.")
        print("  Install with: sudo apt-get install msitools")
        return None
    except Exception as e:
        print(f"  Warning: Error extracting ProductCode: {e}")
        return None
