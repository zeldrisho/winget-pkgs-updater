# WinGet Package Checkver Configurations

This directory contains checkver configuration files that tell the updater how to check for new package versions.

## How It Works

1. **Checkver files** in this repo define how to detect new versions
2. **GitHub Actions** periodically checks for updates
3. **When found**, it:
   - Forks/clones `microsoft/winget-pkgs`
   - Fetches the latest manifest
   - Updates version and SHA256
   - Creates a PR to `microsoft/winget-pkgs`

## File Structure

```
manifests/
├── README.md
├── Publisher.Package.checkver.yaml
└── VNGCorp.Zalo.checkver.yaml
```

Each checkver file contains only the configuration needed to check for updates.

## Checkver Configuration Format

### Example: VNGCorp.Zalo.checkver.yaml

```yaml
# Package identifier
packageIdentifier: VNGCorp.Zalo

# Path in microsoft/winget-pkgs repository
manifestPath: manifests/v/VNGCorp/Zalo

# Version checking method
checkver:
  type: script  # or 'web' for simple scraping
  script: |
    # PowerShell script to get download URL
    try {
      $response = Invoke-WebRequest -Uri "https://zalo.me/download/zalo-pc" -MaximumRedirection 0
      if ($response.Headers.Location) {
        Write-Output $response.Headers.Location.OriginalString
      }
    } catch {
      if ($_.Exception.Response.Headers.Location) {
        Write-Output $_.Exception.Response.Headers.Location.OriginalString
      }
    }
  regex: ZaloSetup-([\d\.]+)\.exe  # Extract version from URL

# Installer URL template for downloading and calculating SHA256
installerUrlTemplate: https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-{version}.exe
```

### Alternative: Simple Web Scraping

```yaml
packageIdentifier: Publisher.Package
manifestPath: manifests/p/Publisher/Package

checkver:
  type: web
  checkUrl: https://example.com/download
  regex: Package-v?([\d\.]+)\.exe

installerUrlTemplate: https://example.com/downloads/Package-{version}.exe
```

## Adding a New Package

1. Create a new checkver file: `manifests/Publisher.Package.checkver.yaml`
2. Define the package identifier and manifest path
3. Configure the version checking method
4. Test locally:
   ```bash
   python scripts/check_version.py manifests/Publisher.Package.checkver.yaml
   ```
5. Add to GitHub Actions workflow matrix

## PR Format

When a new version is detected, the automation will:

1. Fork `microsoft/winget-pkgs` (if not already forked)
2. Create a new branch: `PackageIdentifier-version`
3. Update manifest files with new version and SHA256
4. Create PR with:
   - **Title**: `New version: VNGCorp.Zalo version 25.8.3`
   - **Body**: `Automated by [zeldrisho/winget-pkgs-updater](https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/123456789) in workflow run #123456789.`
   
   The workflow run link is clickable, making it easy for Microsoft reviewers to verify the automation.

## Benefits of This Approach

✅ **Minimal storage** - Only checkver configs in this repo
✅ **Always up-to-date** - Fetches latest manifest from microsoft/winget-pkgs
✅ **Automatic SHA256** - Downloads installer and calculates hash
✅ **Clean PRs** - Creates proper branches and descriptive PR messages
✅ **Scalable** - Easy to add more packages

## References

- [Microsoft WinGet Packages](https://github.com/microsoft/winget-pkgs)
- [WinGet Manifest Schema](https://github.com/microsoft/winget-cli/tree/master/schemas)
