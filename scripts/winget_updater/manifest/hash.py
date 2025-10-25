"""
Hash calculation for installers (SHA256, MSIX signatures, MSI ProductCode)
"""

import os
import sys
import hashlib
import subprocess
import requests
from typing import Optional


def download_file(url: str, filepath: str) -> bool:
    """Download file from URL to filepath with validation"""
    try:
        print(f"Downloading: {url}")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        
        # Track downloaded size
        total_size = 0
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)
                    total_size += len(chunk)
        
        # Verify file was downloaded
        if not os.path.exists(filepath):
            print(f"Error: File was not created: {filepath}")
            return False
        
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            print(f"Error: Downloaded file is empty")
            return False
        
        print(f"Downloaded to: {filepath} ({file_size:,} bytes)")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}", file=sys.stderr)
        return False


def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 hash of file with validation"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    file_size = os.path.getsize(filepath)
    if file_size == 0:
        raise ValueError(f"File is empty: {filepath}")
    
    sha256_hash = hashlib.sha256()
    bytes_read = 0
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            bytes_read += len(byte_block)
    
    if bytes_read != file_size:
        raise ValueError(f"File size mismatch: expected {file_size}, read {bytes_read}")
    
    hash_value = sha256_hash.hexdigest().upper()
    print(f"  Calculated SHA256 for {os.path.basename(filepath)} ({file_size:,} bytes): {hash_value}")
    return hash_value


def calculate_msix_signature_sha256(msix_path: str) -> Optional[str]:
    """
    Calculate SHA256 of MSIX signature using PowerShell.
    Returns None if calculation fails.
    """
    try:
        ps_script = f'''
$packagePath = "{msix_path}"
$sigPath = [System.IO.Path]::GetTempFileName()
$appxFile = Get-AppxPackage -Path $packagePath -PackageTypeFilter Bundle,Main,Resource | Select-Object -First 1
if ($appxFile) {{
    $signHash = (Get-AuthenticodeSignature $packagePath).SignerCertificate.GetCertHashString("SHA256")
    Write-Output $signHash
}} else {{
    # Alternative method: Extract signature from MSIX
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead($packagePath)
    $sigFile = $zip.Entries | Where-Object {{ $_.FullName -eq "AppxSignature.p7x" }}
    if ($sigFile) {{
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($sigFile, $sigPath, $true)
        $sigHash = (Get-FileHash -Path $sigPath -Algorithm SHA256).Hash
        Write-Output $sigHash
    }}
    $zip.Dispose()
    Remove-Item $sigPath -ErrorAction SilentlyContinue
}}
'''
        
        result = subprocess.run(
            ['pwsh', '-Command', ps_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout.strip():
            sig_hash = result.stdout.strip().upper()
            print(f"Calculated SignatureSha256: {sig_hash}")
            return sig_hash
        else:
            print(f"Warning: Could not calculate SignatureSha256: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"Warning: Error calculating SignatureSha256: {e}")
        return None


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
