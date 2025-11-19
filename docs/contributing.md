# Contributing to WinGet Package Updater

Thank you for contributing! This guide explains how to add new packages to the updater.

## Quick Start

1. Fork this repository
2. Create a checkver configuration file
3. Test locally
4. Submit a pull request

## Adding a New Package

### Step 1: Inspect Existing Manifest

Before creating a checkver config, inspect the package structure in microsoft/winget-pkgs:

```powershell
# View available versions
$pkg = "RustDesk/RustDesk"
gh api "/repos/microsoft/winget-pkgs/contents/manifests/r/$pkg" | ConvertFrom-Json | Select-Object name

# Fetch a specific version manifest
$version = "1.3.2"
Invoke-WebRequest "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/r/$pkg/$version/RustDesk.RustDesk.installer.yaml"
```

**Look for**:
- Version format (e.g., `2.3.12.0` vs `1.3.2`)
- Supported architectures (x64, x86, arm64)
- Installer type (MSI, MSIX, EXE, etc.)
- Any unusual fields that might need special handling

### Step 2: Create Checkver Config

Create `manifests/{Publisher}.{Package}.checkver.yaml`:

**For GitHub-hosted packages (recommended)**:
```yaml
checkver:
  type: github
  repo: owner/repo
  appendDotZero: true  # Optional: for 3-part → 4-part version conversion

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**For other sources**:
```yaml
checkver:
  type: script
  script: |
    # PowerShell script to detect version
    $response = Invoke-WebRequest -Uri "https://example.com/version" -UseBasicParsing
    Write-Output $response.Content
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

**Multi-architecture example**:
```yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate:
  x64: "https://github.com/owner/repo/releases/download/v{version}/app-x64.msi"
  arm64: "https://github.com/owner/repo/releases/download/v{version}/app-arm64.msi"
```

**Important Notes**:
- **DO NOT include** `packageIdentifier` or `manifestPath` - they're auto-derived from filename
- **Keep it clean** - No comments in production configs
- **Use placeholders** - `{version}` for full version, `{versionShort}` for version without trailing `.0`

### Step 3: Test Locally

```powershell
# Test version detection
pwsh -File scripts/Check-Version.ps1 manifests/YourPublisher.YourPackage.checkver.yaml

# Check output
Get-Content version_info.json | ConvertFrom-Json | ConvertTo-Json
```

**Expected output**:
```json
{
  "packageIdentifier": "Publisher.Package",
  "version": "1.2.3.0",
  "manifestPath": "manifests/p/Publisher/Package",
  "installerUrl": "https://example.com/1.2.3.0/app.exe",
  "metadata": {
    "releaseNotes": "...",
    "releaseNotesUrl": "..."
  }
}
```

**Exit codes**:
- `0` = New version detected (ready to update)
- `1` = No update needed or check failed

### Step 4: Submit PR

1. Fork this repository
2. Create a new branch: `git checkout -b add-package-name`
3. Add your checkver config to `manifests/`
4. Commit: `git commit -m "Add checkver for Publisher.Package"`
5. Push: `git push origin add-package-name`
6. Create a pull request

## Configuration Best Practices

### Minimal Configs

Only include required fields:
- `checkver` (required)
- `installerUrlTemplate` (required)

Deprecated/auto-derived fields:
- ❌ `packageIdentifier` - Auto-derived from filename
- ❌ `manifestPath` - Auto-derived from packageIdentifier
- ❌ `updateMetadata` - GitHub metadata is fetched automatically

### Clear PowerShell Scripts

For script-based checkver, use clear variable names and logic:

```yaml
checkver:
  type: script
  script: |
    # Fetch version from API
    $apiUrl = "https://api.example.com/latest"
    $response = Invoke-RestMethod -Uri $apiUrl
    $version = $response.version
    Write-Output $version
  regex: "([\\d\\.]+)"
```

### Test First

Always test locally before submitting:

```powershell
pwsh -File scripts/Check-Version.ps1 manifests/Your.Package.checkver.yaml
```

## Architecture Notes

### Auto-Derivation

The system automatically derives:
- **packageIdentifier** from filename: `Microsoft.PowerShell.checkver.yaml` → `Microsoft.PowerShell`
- **manifestPath** via GitHub API detection:
  - Standard: `A.B` → `manifests/a/A/B`
  - Deep nested: `A.B.C.D` → `manifests/a/A/B/C/D`
  - Version subdirectory: `A.B.7` → `manifests/a/A/B/7`

### Manifest Update Strategy

The updater:
1. Copies entire manifest folder from latest version
2. Updates **only necessary fields**:
   - **Always updated**: PackageVersion, InstallerSha256, InstallerUrl
   - **Conditionally updated**: ProductCode (from MSI), ReleaseDate, ReleaseNotes
   - **Preserved**: All other fields (Publisher, License, Tags, etc.)
3. Performs global version string replacement

## Common Patterns

### GitHub Release with appendDotZero

Many packages use 3-part versions in GitHub (e.g., `v7.5.4`) but 4-part in WinGet (e.g., `7.5.4.0`):

```yaml
checkver:
  type: github
  repo: PowerShell/PowerShell
  appendDotZero: true

installerUrlTemplate:
  x64: "https://github.com/PowerShell/PowerShell/releases/download/v{versionShort}/PowerShell-{versionShort}-win-x64.msi"
```

Note: Use `{versionShort}` in URL to get `7.5.4` instead of `7.5.4.0`.

### Date-Based Versions

For packages that use dates as versions:

```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://example.com/changelog.md" -UseBasicParsing
    Write-Output $response.Content
  regex: "Released: (\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"

installerUrlTemplate: "https://download.example.com/latest.zip"
```

### Custom Build Numbers

For packages with build numbers in URLs:

```yaml
checkver:
  type: script
  script: |
    $response = Invoke-RestMethod "https://api.example.com/builds"
    Write-Output "$($response.version)|$($response.buildNumber)"
  regex: "(?P<version>[\\d\\.]+)\\|(?P<build>\\d+)"

installerUrlTemplate: "https://example.com/builds/{build}/installer.exe"
```

## Getting Help

- **Documentation**: See [docs/](../docs/)
- **Examples**: Browse existing checkver files in `manifests/`
- **Issues**: Open an issue for questions
- **Discord**: Join WinGet community Discord

## Code of Conduct

Be respectful and constructive in all interactions.
