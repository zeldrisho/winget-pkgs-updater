# Example Package Configurations

This directory contains example configurations that can be used as templates for new packages.

## VNGCorp.Zalo.yaml

Official Zalo PC messenger application from VNG Corporation.

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
  Zalo PC - Kết nối với những người thân yêu của bạn thông qua tin nhắn, cuộc gọi và nhiều tính năng khác.
tags:
  - messenger
  - chat
  - communication
  - video-call
```

## Creating Your Own

To add a new package, create a file following this template:

```yaml
# Package identifier - must match microsoft/winget-pkgs format
packageIdentifier: Publisher.ApplicationName

# Update method (usually 'web' for web scraping)
updateMethod: web

# URL to check for new versions
checkUrl: https://example.com/download

# Pattern for installer download URL
# Use {version} placeholder where version number appears
installerUrlPattern: https://example.com/files/app-{version}-installer.msi

# System architecture
architecture: x64  # Options: x64, x86, arm64

# Installer type
installerType: msi  # Options: msi, exe, msix, appx, zip, inno, nullsoft

# MSI Product Code (GUID format, use {PRODUCTCODE} if unknown)
productCode: "{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"

# Optional: Release notes URL
releaseNotesUrl: https://example.com/releases

# Publisher name (official company name)
publisher: Publisher Name

# Application display name
packageName: Application Name

# License type
license: Proprietary  # Or: MIT, Apache-2.0, GPL-3.0, Freeware, etc.

# Short description (under 100 characters)
shortDescription: Brief description of the application

# Optional: Detailed description (can be multi-line)
description: |
  Detailed description of what the application does.
  Can span multiple lines.
  Use YAML multi-line string format.

# Optional: Tags for categorization
tags:
  - category1
  - category2
  - category3
```

## Field Guidelines

### Required Fields

Every package must have:
- `packageIdentifier` - Unique ID following `Publisher.AppName` format
- `checkUrl` - URL to check for versions
- `installerUrlPattern` - URL pattern with `{version}` placeholder
- `architecture` - Target system architecture
- `installerType` - Type of installer package
- `publisher` - Official publisher name
- `packageName` - Application display name
- `license` - License type
- `shortDescription` - Brief description

### Optional Fields

Enhance your package with:
- `productCode` - For MSI installers (GUID)
- `releaseNotesUrl` - Link to changelog/release notes
- `description` - Detailed multi-line description
- `tags` - Categorization tags

## Examples by Installer Type

### MSI Installer
```yaml
installerType: msi
productCode: "{12345678-1234-1234-1234-123456789012}"
```

### EXE Installer (Inno Setup)
```yaml
installerType: inno
# or: nullsoft, wix, burn, exe
```

### MSIX/APPX Package
```yaml
installerType: msix
# or: appx
```

### ZIP Archive
```yaml
installerType: zip
# Requires additional NestedInstallerFiles configuration
```

## URL Pattern Examples

### Version in filename
```yaml
installerUrlPattern: https://cdn.example.com/app-{version}-x64.msi
# Matches: app-1.2.3-x64.msi
```

### Version in path
```yaml
installerUrlPattern: https://example.com/releases/{version}/installer.exe
# Matches: releases/1.2.3/installer.exe
```

### Version in both path and filename
```yaml
installerUrlPattern: https://example.com/v{version}/app-{version}.msi
# Matches: v1.2.3/app-1.2.3.msi
```

## Testing Your Configuration

Before committing, test your configuration:

```bash
# Test version detection
python scripts/check_version.py manifests/YourPublisher.YourApp.yaml

# Test manifest generation
python scripts/generate_manifest.py \
  manifests/YourPublisher.YourApp.yaml \
  <version> \
  <installer_url> \
  /tmp/test-output
```

## Next Steps

1. Create your configuration file
2. Test it locally
3. Add it to the workflow matrix in `.github/workflows/update-packages.yml`
4. Commit and push
5. Monitor the Actions tab for results

See [CONTRIBUTING.md](../CONTRIBUTING.md) for detailed guidelines.
