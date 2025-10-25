"""
SHA256 hash calculation and file download
"""

import os
import sys
import hashlib
import requests


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
