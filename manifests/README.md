# Checkver Configuration Guide

This directory contains checkver configuration files that define how to detect new package versions.

## File Naming Convention

Format: `{Publisher}.{Package}.checkver.yaml`

## Configuration Structure

```yaml
packageIdentifier: Publisher.Package
manifestPath: manifests/{first-letter}/{publisher}/{package}
checkver:
  type: script
  script: |
    # PowerShell script to detect version
  regex: "([\\d\\.]+)"
installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

## Required Fields

### packageIdentifier
The unique identifier for the package (must match microsoft/winget-pkgs).

### manifestPath
Path structure in microsoft/winget-pkgs repository:
- Format: `manifests/{first-letter}/{publisher}/{package}`
- First letter is lowercase first character of publisher name

**How to find:**
1. Browse [microsoft/winget-pkgs/manifests](https://github.com/microsoft/winget-pkgs/tree/master/manifests)
2. Navigate through folders to find your package
3. Copy the exact path structure

### checkver
Defines how to detect the latest version.

**Types:**
- `script` - Custom PowerShell script
- `github` - GitHub releases API
- `web` - Simple web scraping

### installerUrlTemplate
URL template with `{version}` placeholder.

## Testing

Test your configuration locally:

```bash
python scripts/check_version.py manifests/YourPackage.checkver.yaml
```

## See Also

- [../CONTRIBUTING.md](../CONTRIBUTING.md) - Adding new packages
- [../docs/TEST_WORKFLOW.md](../docs/TEST_WORKFLOW.md) - Testing workflow
