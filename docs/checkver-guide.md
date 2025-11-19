# Checkver Configuration Guide

Checkver files define how to detect new package versions. They use YAML format and support both GitHub API and custom PowerShell scripts.

## File Naming Convention

Format: `{Publisher}.{Package}.checkver.yaml`

Place files in the `manifests/` directory.

**Examples**:
- `manifests/Microsoft.PowerShell.checkver.yaml`
- `manifests/RustDesk.RustDesk.checkver.yaml`

## Auto-Derived Fields

The following fields are **automatically calculated** and should NOT be specified:

### packageIdentifier
Derived from filename:
- `Microsoft.PowerShell.checkver.yaml` → `Microsoft.PowerShell`

### manifestPath
Derived from packageIdentifier with intelligent pattern detection:
- **Standard**: `Microsoft.PowerShell` → `manifests/m/Microsoft/PowerShell`
- **Deep nested**: `Microsoft.VisualStudio.2022.Community` → `manifests/m/Microsoft/VisualStudio/2022/Community`
- **Version subdirectory**: `RoyalApps.RoyalTS.7` → `manifests/r/RoyalApps/RoyalTS/7`

The system queries GitHub API to detect which pattern exists.

## Configuration Types

### GitHub-Based (Recommended)

For packages hosted on GitHub:

```yaml
checkver:
  type: github
  repo: owner/repo
  appendDotZero: true  # Optional: 3-part → 4-part version conversion

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Features**:
- Automatically fetches latest release from GitHub API
- Extracts ReleaseNotes and ReleaseNotesUrl automatically
- Use `appendDotZero: true` for packages using 4-part versions (e.g., `7.5.4.0`)

**Placeholders**:
- `{version}` - Full version (e.g., `7.5.4.0`)
- `{versionShort}` - Version without trailing `.0` (e.g., `7.5.4`)

### Script-Based (Advanced)

For custom version detection:

```yaml
checkver:
  type: script
  script: |
    # PowerShell code that outputs version string
    $response = Invoke-WebRequest -Uri "https://example.com/version" -UseBasicParsing
    Write-Output $response.Content
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

**Features**:
- Executes PowerShell 7.5+ script (30-second timeout)
- Supports regex for version extraction
- Can extract custom metadata via named groups

#### Regex Replace Pattern

Transform matched strings:

```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://example.com/release" -UseBasicParsing
    Write-Output $response.Content
  regex: "(\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"  # MM/DD/YYYY → YYYY.MM.DD

installerUrlTemplate: "https://example.com/{version}/app.exe"
```

Use `${1}`, `${2}`, etc. to reference capture groups.

#### Custom Metadata Extraction

Use PowerShell named groups for custom placeholders:

```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://example.com/release" -UseBasicParsing
    Write-Output $response.Content
  regex: "(?P<version>[\\d\\.]+)\\|(?P<build>[^\\|]+)"

installerUrlTemplate: "https://example.com/app-{build}.zip"
```

Note: PowerShell uses `(?P<name>...)` for named groups, not `(?<name>...)`.

## Multi-Architecture Support

For packages with multiple architectures:

```yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate:
  x64: "https://example.com/{version}-x64.exe"
  x86: "https://example.com/{version}-x86.exe"
  arm64: "https://example.com/{version}-arm64.exe"
```

The system will:
1. Download and calculate SHA256 for each architecture
2. Extract ProductCode from MSI files (per architecture)
3. Update manifest with multi-arch hashes

## Manifest Update Behavior

When a new version is detected:

### Always Updated
- `PackageVersion` - Set to new version
- `InstallerSha256` - Recalculated from downloaded installer
- `InstallerUrl` - Updated if contains `{version}` placeholder
- `SignatureSha256` - Recalculated for MSIX packages

### Conditionally Updated
Only if field exists in old manifest:
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
- All other fields not listed above

## Examples

### Example 1: GitHub with Multi-Architecture

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

Note: GitHub tag is `v7.5.4` but WinGet version becomes `7.5.4.0` due to `appendDotZero`.

### Example 2: Simple GitHub Package

```yaml
checkver:
  type: github
  repo: rustdesk/rustdesk

installerUrlTemplate:
  x86: "https://github.com/rustdesk/rustdesk/releases/download/{version}/rustdesk-{version}-x86-sciter.exe"
  x64: "https://github.com/rustdesk/rustdesk/releases/download/{version}/rustdesk-{version}-x86_64.exe"
```

### Example 3: Script-Based with Date Transform

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

Transforms `02/15/2024` → `2024.02.15`

## Testing

Test your configuration locally:

```powershell
# Test version detection
pwsh -File scripts/Check-Version.ps1 manifests/YourPackage.checkver.yaml

# View JSON output
Get-Content version_info.json | ConvertFrom-Json | ConvertTo-Json
```

**Expected output**:
```json
{
  "packageIdentifier": "Publisher.Package",
  "version": "1.2.3.0",
  "manifestPath": "manifests/p/Publisher/Package",
  "installerUrl": "https://example.com/1.2.3.0/app.exe",
  "releaseNotes": "What's new...",
  "releaseNotesUrl": "https://github.com/owner/repo/releases/tag/v1.2.3"
}
```

**Exit codes**:
- `0` - New version detected (version_info.json created)
- `1` - No update needed or check failed

## Troubleshooting

### Version Not Detected
- Check PowerShell script syntax: `pwsh -Command "your script"`
- Verify regex pattern captures version correctly
- Ensure script outputs to stdout (use `Write-Output`)

### Wrong Manifest Path
- Verify package identifier format in filename
- Check if package exists in microsoft/winget-pkgs
- System auto-detects standard/deep-nested/version-subdirectory patterns

### ProductCode Not Updating
- Only updates if `ProductCode` field exists in old manifest
- Requires MSI installer (not EXE or MSIX)
- Check that file is actually an MSI

### Metadata Not Fetching
- Only works for `type: github` checkver
- Check repo format is `owner/repo`
- Verify GitHub API access (no token needed for public repos)
