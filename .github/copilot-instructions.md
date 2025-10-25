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
   - Write checkver YAML following standard patterns
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
packageIdentifier: Publisher.Package
manifestPath: manifests/{first-letter}/{publisher}/{package}

checkver:
  type: github
  repo: owner/repo  # GitHub repository (e.g., PowerShell/PowerShell)
  appendDotZero: true  # Optional: append .0 to 3-part versions (7.5.4 -> 7.5.4.0)

# Optional: fetch release metadata from GitHub
updateMetadata:
  - ReleaseNotes
  - ReleaseNotesUrl

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Key Features:**
- **Type**: `github` - Fetches latest release from GitHub API
- **appendDotZero**: Set to `true` to automatically append `.0` to 3-part versions
  - Example: GitHub tag `v7.5.4` becomes WinGet version `7.5.4.0`
  - Useful for packages like PowerShell, SeelenUI that use 4-part versions in manifests
- **updateMetadata**: Automatically fetches ReleaseNotes and ReleaseNotesUrl from GitHub
  - Only updates these fields if they already exist in the old manifest

**Standard Placeholders:**
- `{version}` - Full version (e.g., 2.3.12.0 or 7.5.4.0)
- `{versionShort}` - Version without trailing .0 (e.g., 2.3.12 or 7.5.4)
  - Used for GitHub tags that don't include the `.0` suffix

### Script-Based Checkver (Advanced)

**Basic Structure:**
```yaml
packageIdentifier: Publisher.Package
manifestPath: manifests/{first-letter}/{publisher}/{package}
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
regex: "(?P<version>[\\d\\.]+)\\|(?P<build>[^\\|]+)"
installerUrlTemplate: "https://example.com/app-{build}.zip"
```

**Regex Replace Pattern:**
Transform matched strings using `replace` field (similar to scoop's checkver):
```yaml
# Example: Convert date MM/DD/YYYY to version YYYY.MM.DD
regex: "(\\d{2})/(\\d{2})/(\\d{4})"
replace: "${3}.${1}.${2}"  # Outputs: 2025.10.13
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
- `ProductCode`: Updated if provided (multi-arch supported)
- `RelativeFilePath`: Updated via global version string replacement

**Fields conditionally updated** (only if already exist in old manifest):
- `ReleaseDate`: Always updated to current date (if field exists)
- `ReleaseNotes`: Updated from GitHub API (if field exists and checkver type is 'github')
- `ReleaseNotesUrl`: Updated from GitHub API (if field exists and checkver type is 'github')

**All other fields**: Preserved unchanged from previous version (Publisher, License, Description, Tags, Copyright, etc.)

**No configuration needed** - the system intelligently detects which fields exist and updates appropriately.

Example for GitHub-based packages:
```yaml
checkver:
  type: github
  repo: owner/repo
  regex: "v?([\\d\\.]+)"
# System automatically handles all field updates based on manifest structure
```

**Fetching from Raw Sources:**
For packages where version info comes from raw text files (like documentation or release notes):
```yaml
# Example: Sysinternals Suite uses static download URLs
# Version is determined by documentation date in GitHub markdown file
checkver:
  script: |
    $response = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/..." -UseBasicParsing
    Write-Output $response.Content
  regex: "ms\\.date: (\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"  # Converts MM/DD/YYYY to YYYY.MM.DD

installerUrlTemplate:
  x64: "https://download.example.com/files/Package.zip"
  # URL doesn't change, but version metadata from raw source is used
```
The updater:
1. Scrapes version info from raw sources (docs, changelogs, etc.)
2. Fetches existing manifests from microsoft/winget-pkgs using `manifestPath`
3. Copies the latest version folder and updates version strings + SHA256 hashes
4. Creates a new version folder with updated manifests

**Manifest Path Structure:**
The `manifestPath` follows WinGet's folder structure:
```
manifests/{first-letter}/{publisher}/{package}/{version}/
```
Examples:
- `manifests/m/Microsoft/Sysinternals/Suite/2025.10.13/`
- `manifests/s/Seelen/SeelenUI/2.0.0/`
- `manifests/v/VNGCorp/Zalo/24.10.2/`

The path can be longer than the basic structure as needed.

## Key Concepts

- **Manifest Copy & Update Strategy:** System copies entire manifest folder from previous version, then selectively updates only necessary fields
- **Required Field Updates:** PackageVersion, InstallerSha256, URLs with {version} placeholder are always updated
- **Conditional Field Updates:** ReleaseDate/ReleaseNotes/ReleaseNotesUrl are only updated if they exist in old manifest
- **Global String Replacement:** All occurrences of old version are replaced with new version (handles RelativeFilePath, DisplayVersion, etc.)
- **Field Preservation:** All other fields (Publisher, License, Tags, Copyright, etc.) remain unchanged from previous version
- **PowerShell Scripts:** Use `pwsh` for version detection (30s timeout)
- **Python Named Groups:** Use `(?P<name>...)` NOT `(?<name>...)`
- **MSIX Packages:** Require both SHA256 and SignatureSha256

## Testing

```bash
python3 scripts/check_version.py manifests/Package.checkver.yaml
```

## Environment

- **Required:** `WINGET_PKGS_TOKEN` (GitHub token with repo + workflow scopes)
- **Optional:** `WINGET_FORK_REPO` (defaults to `{owner}/winget-pkgs`)
- **Runtime:** Ubuntu 24.04, Python 3.11+, PowerShell 7.5+

