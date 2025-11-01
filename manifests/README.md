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

**Advanced script with metadata extraction:**
```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://example.com/release" -UseBasicParsing
    Write-Output $response.Content
  regex: "(?P<version>[\\d\\.]+)\\|(?P<build>[^\\|]+)"

installerUrlTemplate: "https://example.com/app-{build}.zip"
```

**Regex replace pattern (transform versions):**
```yaml
checkver:
  type: script
  script: |
    # PowerShell code
  regex: "(\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"  # MM/DD/YYYY → YYYY.MM.DD

installerUrlTemplate: "https://example.com/{version}/app.exe"
```

## Auto-Derived Fields

These fields are **automatically calculated** from the filename and do NOT need to be specified:

### packageIdentifier
Automatically derived from filename.
- Example: `Microsoft.PowerShell.checkver.yaml` → `Microsoft.PowerShell`

### manifestPath
Automatically derived from packageIdentifier with intelligent pattern detection:
- **Standard**: `Microsoft.PowerShell` → `manifests/m/Microsoft/PowerShell`
- **Deep nested**: `Microsoft.VisualStudio.2022.Community` → `manifests/m/Microsoft/VisualStudio/2022/Community`
- **Version subdirectory**: `RoyalApps.RoyalTS.7` → `manifests/r/RoyalApps/RoyalTS/7`
- **Simple**: `VNGCorp.Zalo` → `manifests/v/VNGCorp/Zalo`

The system queries GitHub API to detect which pattern exists.

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
- Automatically fetches latest release from GitHub API
- Extracts ReleaseNotes and ReleaseNotesUrl automatically
- Use `appendDotZero: true` for packages using 4-part versions (e.g., 7.5.4.0)
- No additional configuration needed for metadata

**Script type** (advanced):
```yaml
checkver:
  type: script
  script: |
    # PowerShell code that outputs version string
    $response = Invoke-WebRequest -Uri "https://example.com" -UseBasicParsing
    Write-Output $response.Content
  regex: "([\\d\\.]+)"
```
- Executes PowerShell 7.5+ script (30-second timeout)
- Supports custom metadata via Python named groups: `(?P<name>...)`
- Use `replace` field for version transformation

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

**Why removed?**
These fields were redundant and error-prone. The new auto-derivation system:
- Reduces configuration size by ~30%
- Eliminates misconfiguration errors
- Automatically handles complex manifest path patterns

## Manifest Update Behavior

When a new version is detected, the system:

### Always Updated
- `PackageVersion` - Set to new version
- `InstallerSha256` - Recalculated from downloaded installer
- `InstallerUrl` - Updated if contains `{version}` placeholder
- `SignatureSha256` - Recalculated for MSIX packages

### Conditionally Updated (only if field exists in old manifest)
- `ProductCode` - Automatically extracted from MSI files
- `ReleaseDate` - Set to current date
- `ReleaseNotes` - Fetched from GitHub API (for GitHub checkver type)
- `ReleaseNotesUrl` - Fetched from GitHub API (for GitHub checkver type)
- `RelativeFilePath` - Updated via global version string replacement
- `DisplayVersion` - Updated via global version string replacement

### Always Preserved
- `Publisher`, `PublisherUrl`, `PublisherSupportUrl`
- `Author`, `Copyright`, `License`, `LicenseUrl`
- `Description`, `Moniker`, `Tags`
- `PackageName`, `PackageLocale`
- `Documentations`, `ReleaseNotesUrl` (if not GitHub)
- All other fields not listed above

## Testing

Test your configuration locally:

```bash
# Test version detection
python scripts/check_version.py manifests/YourPackage.checkver.yaml

# View JSON output
cat version_info.json | jq .
```

**Expected output:**
```json
{
  "packageIdentifier": "Publisher.Package",
  "version": "1.2.3.0",
  "manifestPath": "manifests/p/Publisher/Package",
  "metadata": {
    "releaseNotes": "What's new...",
    "releaseNotesUrl": "https://github.com/owner/repo/releases/tag/v1.2.3"
  }
}
```

**Exit codes:**
- `0` - New version detected (version_info.json created)
- `1` - No update needed or check failed

## Examples

### Example 1: GitHub-hosted with Multi-Architecture
```yaml
checkver:
  type: github
  repo: PowerShell/PowerShell
  appendDotZero: true

installerUrlTemplate:
  x64: "https://github.com/PowerShell/PowerShell/releases/download/v{versionShort}/PowerShell-{versionShort}-win-x64.msi"
  x86: "https://github.com/PowerShell/PowerShell/releases/download/v{versionShort}/PowerShell-{versionShort}-win-x86.msi"
  arm64: "https://github.com/PowerShell/PowerShell/releases/download/v{versionShort}/PowerShell-{versionShort}-win-arm64.msi"
```
**Note:** GitHub tag is `v7.5.4` but WinGet version becomes `7.5.4.0` due to `appendDotZero`.

### Example 2: Simple GitHub Package
```yaml
checkver:
  type: github
  repo: rustdesk/rustdesk

installerUrlTemplate:
  x86: "https://github.com/rustdesk/rustdesk/releases/download/{version}/rustdesk-{version}-x86-sciter.exe"
  x64: "https://github.com/rustdesk/rustdesk/releases/download/{version}/rustdesk-{version}-x86_64.exe"
```

### Example 3: Script-based with Date Transform
```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/org/repo/main/docs/version.md" -UseBasicParsing
    Write-Output $response.Content
  regex: "ms\\.date: (\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"

installerUrlTemplate:
  x64: "https://download.example.com/Package.zip"
```
**Note:** Transforms `02/15/2024` → `2024.02.15`

## Troubleshooting

### Version Not Detected
- Check PowerShell script syntax (use `pwsh -Command "..."` to test)
- Verify regex pattern captures version correctly
- Ensure script outputs to stdout (use `Write-Output`)

### Wrong Manifest Path
- Verify package identifier format in filename
- Check if package exists in microsoft/winget-pkgs
- System auto-detects standard/deep-nested/version-subdirectory patterns

### ProductCode Not Updating
- Only updates if `ProductCode` field exists in old manifest
- Requires MSI installer (not EXE or MSIX)
- Check that msitools is installed

### Metadata Not Fetching
- Only works for `type: github` checkver
- Check repo format is `owner/repo`
- Verify GitHub API access (no token needed for public repos)

## See Also

- [../CONTRIBUTING.md](../CONTRIBUTING.md) - Adding new packages
- [../.github/copilot-instructions.md](../.github/copilot-instructions.md) - Complete documentation
