# Example Package Configurations

This directory contains YAML configuration files for each package to monitor.

## Configuration Format

Each package should have its own YAML file named `Publisher.AppName.yaml`.

### Example: VNGCorp.Zalo.yaml

```yaml
packageIdentifier: VNGCorp.Zalo
updateMethod: web
checkUrl: https://www.zalo.me/download
installerUrlPattern: https://res-zalo-pc-stc.zadn.vn/win/Zalo-{version}-win64.msi
architecture: x64
installerType: msi
productCode: "{PRODUCTCODE}"
releaseNotesUrl: https://www.zalo.me
publisher: VNG Corporation
packageName: Zalo
license: Proprietary
shortDescription: Zalo - Nhắn Gửi Yêu Thương
description: |
  Zalo PC - Kết nối với những người thân yêu của bạn.
tags:
  - messenger
  - chat
  - communication
  - video-call
```

## Fields Description

- **packageIdentifier**: Unique identifier in format `Publisher.AppName`
- **updateMethod**: Method to check for updates (`web` or `api`)
- **checkUrl**: URL to check for version information
- **installerUrlPattern**: URL pattern for installer download (use `{version}` placeholder)
- **architecture**: System architecture (`x64`, `x86`, `arm64`)
- **installerType**: Type of installer (`msi`, `exe`, `msix`, `appx`)
- **productCode**: Product code for MSI installers (use `{PRODUCTCODE}` if unknown)
- **releaseNotesUrl**: URL to release notes (optional)
- **publisher**: Publisher/company name
- **packageName**: Display name of the package
- **license**: License type (e.g., `Proprietary`, `MIT`, `GPL-3.0`)
- **shortDescription**: Brief description
- **description**: Detailed description (optional)
- **tags**: List of relevant tags (optional)

## Adding a New Package

1. Create a new YAML file in this directory using the format above
2. Add the file path to the workflow matrix in `.github/workflows/update-packages.yml`
3. Test the configuration:
   ```bash
   python scripts/check_version.py manifests/YourPublisher.YourApp.yaml
   ```

Or use the helper script:
```bash
python scripts/add_package.py
```
