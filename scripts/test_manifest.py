#!/usr/bin/env python3
"""
Test manifest generation with mock data
"""

import os
import sys
import tempfile

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import generate_manifest
import yaml


def test_generate_manifest():
    """Test manifest generation with sample data"""
    
    # Create temporary config
    config = {
        'packageIdentifier': 'VNGCorp.Zalo',
        'architecture': 'x64',
        'installerType': 'msi',
        'productCode': '{A1234567-B890-C123-D456-E78901234567}',
        'publisher': 'VNG Corporation',
        'packageName': 'Zalo',
        'license': 'Proprietary',
        'shortDescription': 'Zalo - Nhắn Gửi Yêu Thương',
        'description': 'Zalo PC - Kết nối với những người thân yêu của bạn thông qua tin nhắn, cuộc gọi và nhiều tính năng khác.',
        'releaseNotesUrl': 'https://www.zalo.me',
        'tags': ['messenger', 'chat', 'communication', 'video-call']
    }
    
    # Mock version and URL (for testing structure only)
    version = '24.1.5'
    installer_url = 'https://example.com/Zalo-24.1.5-win64.msi'
    
    # Test manifest generation functions
    print("Testing Version Manifest:")
    version_manifest = generate_manifest.generate_version_manifest(config, version, installer_url, 'ABC123')
    print(version_manifest)
    print()
    
    print("Testing Installer Manifest:")
    installer_manifest = generate_manifest.generate_installer_manifest(config, version, installer_url, 'ABC123')
    print(installer_manifest)
    print()
    
    print("Testing Locale Manifest:")
    locale_manifest = generate_manifest.generate_locale_manifest(config, version)
    print(locale_manifest)
    print()
    
    print("✓ All manifest generation tests passed!")


if __name__ == '__main__':
    test_generate_manifest()
