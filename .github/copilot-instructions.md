# WinGet Package Updater - AI Coding Agent Instructions

## Project Overview

Automated tool that monitors software packages and creates pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when new versions are detected. Runs on GitHub Actions, checking versions via PowerShell scripts.

## Architecture

1. **Version Detection** (`scripts/check_version.py`)
   - Executes PowerShell scripts to scrape version info
   - Supports custom metadata extraction via named regex groups
   - Outputs version info JSON

2. **Manifest Update** (`scripts/update_manifest.py`)
   - Fetches manifests from microsoft/winget-pkgs
   - Downloads installers to calculate SHA256 hashes
   - Performs global version string replacement across manifests

3. **PR Management**
   - Smart PR detection (skip if OPEN/MERGED, retry if CLOSED)
   - Creates branch in user's fork
   - Submits PR to upstream

## Workflow for Adding New Manifests

**When user requests to add a new manifest:**

1. **User Provides:**
   - Package name/identifier
   - Example checkver template or reference

2. **Agent Must:**
   - Fetch latest version manifest from microsoft/winget-pkgs
   - Scan all manifest files (installer, locale, version YAML)
   - Analyze field structure and identify any unusual fields

3. **Report Findings:**
   - **If unusual fields detected:** Notify user about fields that may require new features
     - Examples: Custom installer switches, nested architectures, special dependencies, etc.
     - Wait for user decision before proceeding
   - **If standard fields only:** Proceed to write checkver configuration

4. **Create Checkver:**
   - Write clean, minimal checkver YAML following standard patterns (no comments)
   - Test with `check_version.py` to verify it works

**Example unusual fields to watch for:**
- Non-standard installer types
- Complex ProductCode patterns not covered by current system
- Custom fields beyond ReleaseNotes/ReleaseNotesUrl/ReleaseDate
- Special dependencies or requirements
- Nested or dynamic architecture configurations

## Checkver Configuration

**Before Creating New Checkver:**
Always inspect existing manifests (latest version) on microsoft/winget-pkgs first to understand:
- Current package structure and version format
- Installer URL patterns and architectures supported
- Any special requirements (MSIX signatures, installer switches, etc.)

Example:
```bash
# View existing manifest structure
curl -s "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/r/RustDesk/RustDesk/1.3.2/RustDesk.RustDesk.installer.yaml"
```

### GitHub-Based Checkver (Recommended)

**Simple Format:**
```yaml
checkver:
  type: github
  repo: owner/repo
  appendDotZero: true

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Key Features:**
- **Type**: `github` - Fetches latest release from GitHub API
- **appendDotZero**: Set to `true` to automatically append `.0` to 3-part versions
  - Example: GitHub tag `v7.5.4` becomes WinGet version `7.5.4.0`
  - Useful for packages like PowerShell, SeelenUI that use 4-part versions in manifests
- **Metadata**: ReleaseNotes and ReleaseNotesUrl are ALWAYS fetched from GitHub API
  - Automatically updates if these fields exist in the old manifest
  - No configuration needed

**Standard Placeholders:**
- `{version}` - Full version (e.g., 2.3.12.0 or 7.5.4.0)
- `{versionShort}` - Version without trailing .0 (e.g., 2.3.12 or 7.5.4)
  - Used for GitHub tags that don't include the `.0` suffix

**Auto-Derived Fields:**
The following fields are automatically derived from the filename and NO LONGER need to be specified:
- `packageIdentifier` - Derived from filename (e.g., `Microsoft.PowerShell.checkver.yaml` → `Microsoft.PowerShell`)
- `manifestPath` - Derived from packageIdentifier (e.g., `Microsoft.PowerShell` → `manifests/m/Microsoft/PowerShell`)

### Script-Based Checkver (Advanced)

**Basic Structure:**
```yaml
checkver:
  type: script
  script: |
    # PowerShell code that outputs version string
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

**Custom Metadata (Advanced):**
Use Python named groups to extract additional data:
```yaml
checkver:
  type: script
  script: |
    # PowerShell code
  regex: "(?P<version>[\\d\\.]+)\\|(?P<build>[^\\|]+)"

installerUrlTemplate: "https://example.com/app-{build}.zip"
```

**Regex Replace Pattern:**
Transform matched strings using `replace` field (similar to scoop's checkver):
```yaml
checkver:
  type: script
  script: |
    # PowerShell code
  regex: "(\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"

installerUrlTemplate: "https://example.com/{version}/app.exe"
```
Use `${1}`, `${2}`, etc. to reference capture groups.

### Multi-Architecture URLs

```yaml
installerUrlTemplate:
  x64: "https://example.com/{version}-win64.zip"
  arm64: "https://example.com/{version}-arm64.zip"
```

**Automatic Manifest Update Process:**
The system copies the entire manifest folder from the previous version and updates only necessary fields:

**Fields that MUST change** (automatically updated):
- `PackageVersion`: Updated to new version
- `InstallerSha256`: Recalculated from downloaded installer
- `SignatureSha256`: Recalculated if MSIX package
- `InstallerUrl`: Updated if contains `{version}` placeholder
- `RelativeFilePath`: Updated via global version string replacement

**Fields conditionally updated** (only if already exist in old manifest):
- `ProductCode`: Automatically extracted from MSI files and updated (if field exists in old manifest)
- `ReleaseDate`: Always updated to current date (if field exists)
- `ReleaseNotes`: Updated from GitHub API (if field exists and checkver type is 'github')
- `ReleaseNotesUrl`: Updated from GitHub API (if field exists and checkver type is 'github')

**All other fields**: Preserved unchanged from previous version (Publisher, License, Description, Tags, Copyright, etc.)

**No configuration needed** - the system intelligently detects which fields exist in the template manifest and updates appropriately.

Example checkver (clean, no comments):
```yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.msi"
```

**Fetching from Raw Sources:**
For packages where version info comes from raw text files (like documentation or release notes):
```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/..." -UseBasicParsing
    Write-Output $response.Content
  regex: "ms\\.date: (\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"

installerUrlTemplate:
  x64: "https://download.example.com/files/Package.zip"
```
The updater:
1. Scrapes version info from raw sources (docs, changelogs, etc.)
2. Auto-derives `manifestPath` from package identifier
3. Fetches existing manifests from microsoft/winget-pkgs
4. Copies the latest version folder and updates version strings + SHA256 hashes
5. Automatically extracts ProductCode from MSI files (if ProductCode field exists in old manifest)
6. Creates a new version folder with updated manifests

**Manifest Path Auto-Derivation:**
The system automatically calculates `manifestPath` from the checkver filename:
```
Filename: Microsoft.PowerShell.checkver.yaml
  → packageIdentifier: Microsoft.PowerShell
  → manifestPath: manifests/m/Microsoft/PowerShell

Filename: VNGCorp.Zalo.checkver.yaml
  → packageIdentifier: VNGCorp.Zalo
  → manifestPath: manifests/v/VNGCorp/Zalo
```

## Key Concepts

- **Auto-Derived Fields:** `packageIdentifier` and `manifestPath` are automatically derived from filename
- **GitHub Metadata:** For GitHub-based packages, ReleaseNotes/ReleaseNotesUrl are ALWAYS fetched (no config needed)
- **Manifest Copy & Update Strategy:** System copies entire manifest folder from previous version, then selectively updates only necessary fields
- **Required Field Updates:** PackageVersion, InstallerSha256, URLs with {version} placeholder are always updated
- **Conditional Field Updates:** Only updated if they exist in old manifest:
  - ReleaseDate/ReleaseNotes/ReleaseNotesUrl
  - ProductCode (automatically extracted from MSI files)
  - SignatureSha256 (automatically calculated for MSIX packages)
- **Global String Replacement:** All occurrences of old version are replaced with new version (handles RelativeFilePath, DisplayVersion, etc.)
- **Field Preservation:** All other fields (Publisher, License, Tags, Copyright, etc.) remain unchanged from previous version
- **PowerShell Scripts:** Use `pwsh` for version detection (30s timeout)
- **Python Named Groups:** Use `(?P<name>...)` NOT `(?<name>...)`
- **Clean Checkver Files:** Do NOT add comments to checkver YAML files - keep them minimal and clean
- **Installer URL Template:** MUST be specified - handles version placeholders and multi-architecture support

## Testing

```bash
python3 scripts/check_version.py manifests/Package.checkver.yaml
```

## Environment

- **Required:** `WINGET_PKGS_TOKEN` (GitHub token with repo + workflow scopes)
- **Optional:** `WINGET_FORK_REPO` (defaults to `{owner}/winget-pkgs`)
- **Runtime:** Ubuntu 24.04, Python 3.11+, PowerShell 7.5+

