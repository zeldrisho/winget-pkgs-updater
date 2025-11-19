# Checkver Configurations

This directory contains checkver configuration files for automated package updates.

## Quick Reference

### File Naming
Format: `{Publisher}.{Package}.checkver.yaml`

Example: `Microsoft.PowerShell.checkver.yaml`

### Basic Configuration

**GitHub Release:**
```yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Custom Script:**
```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://example.com/version" -UseBasicParsing
    Write-Output $response.Content
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

### Auto-Derived Fields

The following fields are automatically derived and should **NOT** be included:
- ❌ `packageIdentifier` - Derived from filename
- ❌ `manifestPath` - Detected via GitHub API

## Documentation

For complete documentation, see:
- **[docs/checkver-guide.md](../docs/checkver-guide.md)** - Complete configuration reference
- **[docs/quick-start.md](../docs/quick-start.md)** - Quick start guide
- **[docs/contributing.md](../docs/contributing.md)** - How to add packages

## Testing

```powershell
# Test version detection
pwsh -File scripts/Check-Version.ps1 manifests/YourPackage.checkver.yaml

# View output
Get-Content version_info.json | ConvertFrom-Json | ConvertTo-Json
```

**Exit codes:**
- `0` - New version detected
- `1` - No update needed

## Examples

Browse the existing checkver files in this directory for real-world examples.

## Need Help?

- See [docs/checkver-guide.md](../docs/checkver-guide.md) for detailed documentation
- See [docs/contributing.md](../docs/contributing.md) for adding new packages
- Open an issue if you have questions
