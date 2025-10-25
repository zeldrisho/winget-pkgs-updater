# Checkver Configuration Guide

This directory contains checkver configuration files that define how to detect new package versions.

## File Naming Convention

Format: `{Publisher}.{Package}.checkver.yaml`

The filename determines the package identifier and manifest path automatically.

## Configuration Structure

**Minimal GitHub-based configuration:**
```yaml
checkver:
  type: github
  repo: owner/repo
  appendDotZero: true  # Optional: append .0 to 3-part versions

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Script-based configuration:**
```yaml
checkver:
  type: script
  script: |
    # PowerShell script to detect version
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

## Auto-Derived Fields

These fields are **automatically calculated** from the filename and do NOT need to be specified:

### packageIdentifier
Automatically derived from filename.
- Example: `Microsoft.PowerShell.checkver.yaml` → `Microsoft.PowerShell`

### manifestPath
Automatically derived from packageIdentifier.
- Example: `Microsoft.PowerShell` → `manifests/m/Microsoft/PowerShell`
- Example: `VNGCorp.Zalo` → `manifests/v/VNGCorp/Zalo`

## Required Fields

### checkver
Defines how to detect the latest version.

**GitHub type** (recommended):
```yaml
checkver:
  type: github
  repo: owner/repo
  appendDotZero: true  # Optional: for 3-part → 4-part version conversion
```
- Automatically fetches ReleaseNotes and ReleaseNotesUrl
- No additional configuration needed for metadata

**Script type** (advanced):
```yaml
checkver:
  type: script
  script: |
    # PowerShell code that outputs version string
  regex: "([\\d\\.]+)"
```

### installerUrlTemplate
URL template with placeholders:
- `{version}` - Full version (e.g., 7.5.4.0)
- `{versionShort}` - Version without trailing .0 (e.g., 7.5.4)

**Single architecture:**
```yaml
installerUrlTemplate: "https://example.com/{version}/app.exe"
```

**Multi-architecture:**
```yaml
installerUrlTemplate:
  x64: "https://example.com/{version}-x64.exe"
  arm64: "https://example.com/{version}-arm64.exe"
```

## Deprecated Fields

The following fields are **no longer needed** and will be ignored:
- ❌ `packageIdentifier` - Auto-derived from filename
- ❌ `manifestPath` - Auto-derived from packageIdentifier
- ❌ `updateMetadata` - GitHub metadata is fetched automatically

## Testing

Test your configuration locally:

```bash
python scripts/check_version.py manifests/YourPackage.checkver.yaml
```

## See Also

- [../CONTRIBUTING.md](../CONTRIBUTING.md) - Adding new packages
- [../.github/copilot-instructions.md](../.github/copilot-instructions.md) - Complete documentation
