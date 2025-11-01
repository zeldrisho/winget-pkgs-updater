# Contributing Guide

Thank you for contributing to WinGet Package Updater!

## Adding New Packages

### Step 1: Inspect Existing Manifest

Before creating a checkver config, inspect the package structure in microsoft/winget-pkgs:

```bash
# View available versions
curl -s "https://api.github.com/repos/microsoft/winget-pkgs/contents/manifests/{first-letter}/{publisher}/{package}" | jq -r '.[].name'

# Fetch a specific version manifest
curl -s "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/{first-letter}/{publisher}/{package}/{version}/{PackageIdentifier}.installer.yaml"
```

**Example:**
```bash
curl -s "https://api.github.com/repos/microsoft/winget-pkgs/contents/manifests/r/RustDesk/RustDesk" | jq -r '.[].name'
curl -s "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/r/RustDesk/RustDesk/1.3.2/RustDesk.RustDesk.installer.yaml"
```

**Look for:**
- Version format (e.g., `2.3.12.0` vs `1.3.2`)
- Supported architectures (x64, x86, arm64)
- Installer type (MSI, MSIX, EXE, etc.)
- Any unusual fields that might need special handling

### Step 2: Determine if Special Features Are Needed

**Report to maintainers if you find:**
- Non-standard installer types
- Complex ProductCode patterns
- Custom installer switches
- Nested architectures
- Special dependencies
- Fields beyond standard (Publisher, License, Description, etc.)

### Step 3: Create Checkver Config

Create `manifests/{Publisher}.{Package}.checkver.yaml`:

**For GitHub-hosted packages (recommended):**
```yaml
checkver:
  type: github
  repo: owner/repo
  appendDotZero: true  # Optional: for 3-part → 4-part version conversion

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**For other sources:**
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

**Multi-architecture example:**
```yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate:
  x64: "https://github.com/owner/repo/releases/download/v{version}/app-x64.msi"
  arm64: "https://github.com/owner/repo/releases/download/v{version}/app-arm64.msi"
```

**Important Notes:**
- **DO NOT include** `packageIdentifier` or `manifestPath` - they're auto-derived from filename
- **Keep it clean** - No comments in production configs
- **Use placeholders** - `{version}` for full version, `{versionShort}` for version without trailing `.0`

### Step 4: Test Locally

```bash
# Test version detection for your package
python3 scripts/check_version.py manifests/YourPublisher.YourPackage.checkver.yaml

# Check output
cat version_info.json | jq .
```

**Expected output:**
```json
{
  "packageIdentifier": "Publisher.Package",
  "version": "1.2.3.0",
  "manifestPath": "manifests/p/Publisher/Package",
  "metadata": {
    "releaseNotes": "...",
    "releaseNotesUrl": "..."
  }
}
```

**Exit codes:**
- `0` = New version detected (ready to update)
- `1` = No update needed or check failed

### Step 5: Submit PR

1. Fork this repository
2. Create a new branch
3. Add your checkver config
4. Submit a pull request

## Code Style

- **Minimal configs** - Only include required fields (`checkver`, `installerUrlTemplate`)
- **No deprecated fields** - Don't include `packageIdentifier`, `manifestPath`, `updateMetadata`
- **No comments** - Keep checkver files clean (comments in docs only)
- **Clear PowerShell** - Use clear variable names and logic in scripts
- **Test first** - Always test locally before submitting

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
   - **Always**: PackageVersion, InstallerSha256, InstallerUrl (with `{version}`)
   - **Conditionally**: ProductCode (from MSI), ReleaseDate, ReleaseNotes (if exist)
   - **Preserved**: Everything else (Publisher, License, Tags, Copyright, etc.)
3. Performs global version string replacement (handles RelativeFilePath, DisplayVersion, etc.)

## Questions?

Open an issue or discussion.
