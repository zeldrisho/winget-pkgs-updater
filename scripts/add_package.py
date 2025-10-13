#!/usr/bin/env python3
"""
Helper script to add a new package configuration
"""

import os
import sys
import yaml


def create_package_config():
    """Interactive package configuration creator"""
    print("=== WinGet Package Configuration Creator ===\n")
    
    # Get basic info
    publisher = input("Publisher name (e.g., VNGCorp): ").strip()
    app_name = input("Application name (e.g., Zalo): ").strip()
    package_id = f"{publisher}.{app_name}"
    
    print(f"\nPackage ID will be: {package_id}")
    
    # Get URLs
    check_url = input("Check URL (where to find version info): ").strip()
    installer_pattern = input("Installer URL pattern (use {version} placeholder): ").strip()
    
    # Get installer info
    print("\nArchitecture options: x64, x86, arm64")
    architecture = input("Architecture [x64]: ").strip() or "x64"
    
    print("\nInstaller type options: msi, exe, msix, appx")
    installer_type = input("Installer type [msi]: ").strip() or "msi"
    
    product_code = input("Product code (for MSI, use {PRODUCTCODE} if unknown): ").strip() or "{PRODUCTCODE}"
    
    # Get metadata
    print("\n--- Package Metadata ---")
    package_name = input(f"Display name [{app_name}]: ").strip() or app_name
    short_desc = input("Short description: ").strip()
    description = input("Full description: ").strip()
    license_type = input("License [Proprietary]: ").strip() or "Proprietary"
    release_notes_url = input("Release notes URL (optional): ").strip()
    
    # Get tags
    print("\nTags (comma-separated, e.g., messenger,chat,communication): ")
    tags_input = input("Tags: ").strip()
    tags = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
    
    # Build config
    config = {
        'packageIdentifier': package_id,
        'updateMethod': 'web',
        'checkUrl': check_url,
        'installerUrlPattern': installer_pattern,
        'architecture': architecture,
        'installerType': installer_type,
        'productCode': product_code,
        'publisher': publisher,
        'packageName': package_name,
        'license': license_type,
        'shortDescription': short_desc,
    }
    
    if description:
        config['description'] = description
    if release_notes_url:
        config['releaseNotesUrl'] = release_notes_url
    if tags:
        config['tags'] = tags
    
    # Show preview
    print("\n=== Configuration Preview ===")
    print(yaml.dump(config, sort_keys=False, allow_unicode=True))
    
    # Confirm and save
    save = input("\nSave this configuration? [Y/n]: ").strip().lower()
    if save in ['', 'y', 'yes']:
        manifests_dir = os.path.join(os.path.dirname(__file__), '..', 'manifests')
        os.makedirs(manifests_dir, exist_ok=True)
        
        output_file = os.path.join(manifests_dir, f"{package_id}.yaml")
        with open(output_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, sort_keys=False, allow_unicode=True)
        
        print(f"\n✓ Configuration saved to: {output_file}")
        print(f"\nNext steps:")
        print(f"1. Verify the configuration in {output_file}")
        print(f"2. Add '{output_file}' to the workflow matrix in .github/workflows/update-packages.yml")
        print(f"3. Test the configuration: python scripts/check_version.py {output_file}")
    else:
        print("\nConfiguration not saved.")


if __name__ == '__main__':
    try:
        create_package_config()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
