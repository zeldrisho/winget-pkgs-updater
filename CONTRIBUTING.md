# Contributing Guide

Thank you for your interest in contributing to winget-pkgs-updater! This guide will help you add new packages to be monitored.

## Adding a New Package

### Quick Start with Helper Script

The easiest way to add a package is using the interactive helper script:

```bash
python scripts/add_package.py
```

This will guide you through:
1. Package identification
2. URL configuration
3. Installer details
4. Metadata

### Manual Configuration

If you prefer to create the configuration manually:

#### 1. Create Manifest File

Create a new YAML file in `manifests/` directory:

**File name format:** `Publisher.AppName.yaml`

**Example:** `Microsoft.VisualStudioCode.yaml`

#### 2. Configuration Template

```yaml
packageIdentifier: Publisher.AppName
updateMethod: web
checkUrl: https://example.com/download
installerUrlPattern: https://example.com/app-{version}-win64.msi
architecture: x64
installerType: msi
productCode: "{GUID}"
releaseNotesUrl: https://example.com/releases
publisher: Publisher Name
packageName: Application Name
license: License Type
shortDescription: Brief description
description: |
  Detailed description of the application.
  Can span multiple lines.
tags:
  - tag1
  - tag2
  - tag3
```

#### 3. Field Reference

**Required Fields:**

- `packageIdentifier`: Unique ID in format `Publisher.AppName`
  - Must match the naming convention in microsoft/winget-pkgs
  - Use PascalCase for both publisher and app name

- `checkUrl`: URL to check for version updates
  - Should be the official download page
  - Must be publicly accessible

- `installerUrlPattern`: URL pattern for downloading installers
  - Use `{version}` as placeholder for version number
  - Example: `https://example.com/app-{version}-installer.msi`

- `architecture`: System architecture
  - Options: `x64`, `x86`, `arm64`

- `installerType`: Type of installer
  - Options: `msi`, `exe`, `msix`, `appx`, `zip`, `inno`, `nullsoft`, `wix`, `burn`

- `publisher`: Official publisher/company name

- `packageName`: Display name of the application

- `license`: License type
  - Examples: `MIT`, `Apache-2.0`, `GPL-3.0`, `Proprietary`, `Freeware`

- `shortDescription`: One-line description (under 100 characters)

**Optional Fields:**

- `productCode`: MSI product code GUID
  - Format: `{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}`
  - Use `{PRODUCTCODE}` if unknown

- `description`: Detailed multi-line description

- `releaseNotesUrl`: URL to release notes or changelog

- `tags`: List of relevant tags
  - Use lowercase
  - No spaces (use hyphens)

#### 4. Add to Workflow

Edit `.github/workflows/update-packages.yml`:

```yaml
strategy:
  matrix:
    manifest:
      - manifests/VNGCorp.Zalo.yaml
      - manifests/YourPublisher.YourApp.yaml  # Add your manifest here
```

#### 5. Test Your Configuration

```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Test version detection
python scripts/check_version.py manifests/YourPublisher.YourApp.yaml

# Test manifest generation (with actual version and URL)
python scripts/generate_manifest.py \
  manifests/YourPublisher.YourApp.yaml \
  1.0.0 \
  https://example.com/installer.msi \
  /tmp/test-output
```

#### 6. Commit and Create PR

```bash
git add manifests/YourPublisher.YourApp.yaml
git add .github/workflows/update-packages.yml
git commit -m "Add YourPublisher.YourApp package"
git push origin main
```

## Package Guidelines

### Choosing Packages

Good candidates for automation:
- ✅ Regular release schedule
- ✅ Publicly accessible download page
- ✅ Consistent URL pattern for installers
- ✅ Version information available on download page
- ✅ Already exists in microsoft/winget-pkgs

### Package Naming

Follow microsoft/winget-pkgs conventions:

1. **Publisher Name:**
   - Use official company/organization name
   - PascalCase (e.g., `Microsoft`, `Google`, `VNGCorp`)
   - No spaces or special characters

2. **Application Name:**
   - Use official application name
   - PascalCase (e.g., `VisualStudioCode`, `Chrome`, `Zalo`)
   - Remove common suffixes like "PC", "Desktop" unless necessary

3. **Examples:**
   - ✅ `Microsoft.VisualStudioCode`
   - ✅ `Google.Chrome`
   - ✅ `VNGCorp.Zalo`
   - ❌ `microsoft.visual-studio-code`
   - ❌ `Google.Chrome.Browser`

### URL Patterns

The `installerUrlPattern` must:
- Use `{version}` placeholder exactly where version appears
- Point to direct download links (no redirects if possible)
- Be stable and predictable

**Examples:**

```yaml
# Good: Direct download with clear version
installerUrlPattern: https://example.com/releases/v{version}/app-installer.msi

# Good: Version in filename
installerUrlPattern: https://cdn.example.com/app-{version}-x64.exe

# Acceptable: Multiple version parts
installerUrlPattern: https://example.com/v{version}/app-{version}.msi

# Avoid: Complex or unpredictable URLs
```

## Version Detection

### Web Scraping

The default version detection scrapes the `checkUrl` for version patterns:

1. Looks for common patterns:
   - `AppName-1.2.3-installer.msi`
   - `version: 1.2.3`
   - `v1.2.3`

2. Returns the first valid semantic version found

### Custom Detection

For complex scenarios, you can extend `scripts/check_version.py`:

```python
def get_version_for_specific_app(check_url: str, package_id: str) -> Optional[str]:
    """Custom version detection for specific packages"""
    if package_id == "YourPublisher.YourApp":
        # Your custom logic here
        response = requests.get(check_url)
        # Parse response and extract version
        return extracted_version
    
    return None
```

## Testing

### Unit Tests

Test manifest generation:
```bash
python scripts/test_manifest.py
```

### Integration Tests

Test the full flow:
```bash
# 1. Check version
python scripts/check_version.py manifests/YourApp.yaml

# 2. Generate manifests (requires working installer URL)
python scripts/generate_manifest.py \
  manifests/YourApp.yaml \
  <version> \
  <installer_url> \
  /tmp/test-manifests

# 3. Verify generated files
ls -la /tmp/test-manifests/
```

### Workflow Test

Test via GitHub Actions:
1. Push your changes
2. Go to Actions tab
3. Run "Update WinGet Packages" workflow manually
4. Check logs for errors

## Best Practices

1. **Test Before Committing**
   - Always test version detection
   - Verify URL patterns work
   - Check generated manifests

2. **Keep Configurations Simple**
   - Use standard fields when possible
   - Avoid unnecessary customization
   - Follow microsoft/winget-pkgs conventions

3. **Document Special Cases**
   - Add comments for unusual configurations
   - Note any limitations or known issues

4. **Monitor Your Packages**
   - Check workflow runs after adding packages
   - Verify PRs are created correctly
   - Update configurations if patterns change

## Common Issues

### Version Not Detected

**Problem:** Workflow can't find version on website

**Solutions:**
- Check if website blocks automated requests
- Verify the URL is correct and accessible
- Look at the HTML source to find version patterns
- Implement custom version detection

### Wrong Installer URL

**Problem:** Generated installer URL is incorrect

**Solutions:**
- Double-check the `installerUrlPattern`
- Test the pattern with known versions
- Ensure `{version}` placeholder is correctly positioned

### Manifest Validation Fails

**Problem:** microsoft/winget-pkgs rejects the manifest

**Solutions:**
- Check the [official manifest schema](https://github.com/microsoft/winget-pkgs/tree/master/doc)
- Use microsoft's validation tools
- Compare with existing manifests in winget-pkgs

## Resources

- [WinGet Packages Repository](https://github.com/microsoft/winget-pkgs)
- [WinGet Manifest Schema](https://github.com/microsoft/winget-pkgs/tree/master/doc/manifest/schema)
- [WinGet CLI Documentation](https://learn.microsoft.com/windows/package-manager/)

## Questions?

If you need help:
1. Check existing manifest examples in `manifests/`
2. Review this guide and SETUP.md
3. Look at the workflow logs for error messages
4. Open an issue with details about your package

Thank you for contributing! 🎉
