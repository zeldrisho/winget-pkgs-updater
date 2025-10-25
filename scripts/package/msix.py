"""
MSIX package signature extraction using PowerShell
"""

import subprocess
from typing import Optional


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
