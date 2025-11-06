# WinGet Package Updater - AI Coding Agent Instructions

## Project Overview

Automated tool that monitors software packages and creates pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when new versions are detected. Runs on GitHub Actions, using PowerShell scripts or GitHub API for version detection.

**Key Technologies:** Python 3.11+, PowerShell 7.5+, GitHub CLI (`gh`), PyYAML, `msitools`, `packaging`

## Architecture Overview

This is a **3-stage pipeline** that runs on GitHub Actions:

### Stage 1: Version Detection (`scripts/check_version.py`)
- **STEP 1:** Query microsoft/winget-pkgs API to find latest published version
- **STEP 2:** Execute version check (PowerShell script or GitHub API)
- **STEP 3:** Compare versions - exit 0 if new version found, exit 1 if same
- **Output:** `version_info.json` containing `{packageIdentifier, version, manifestPath, metadata}`
- **Supports:** Custom metadata extraction via Python named groups `(?P<name>...)`

### Stage 2: PR Gate Check (GitHub Actions Workflow)
- **STEP 4:** Search microsoft/winget-pkgs for existing PRs matching package+version
  - **OPEN or MERGED** → Skip (already submitted/accepted)
  - **CLOSED** → Check if branch exists on fork
    - Branch exists → Skip (avoid duplicate PR)
    - Branch deleted → Continue (can retry)
- **Purpose:** Prevents duplicate PRs and respects upstream decisions
- **Only proceeds to Stage 3** if no blocking conditions found

### Stage 3: Manifest Update (`scripts/update_manifest.py`)
- **STEP 5:** Clone fork of microsoft/winget-pkgs
- **STEP 6:** Fetch existing manifests for latest version
- **STEP 7:** Download installers and calculate SHA256 hashes (supports multi-arch)
- **STEP 8:** Extract ProductCode from MSI files using `msitools`
- **STEP 9:** Copy manifest folder and apply updates (version replacement + field updates)
- **STEP 10:** Create branch, commit, push to fork, open PR
- **Strategy:** Copy entire manifest folder → selective field updates → global version string replacement

## Code Organization

### Module Structure (`scripts/`)

**Core Scripts:**
- `check_version.py` - Entry point for version detection (Stage 1)
- `update_manifest.py` - Entry point for manifest updates (Stage 3)
- `config.py` - Checkver YAML loader with auto-derivation logic
- `version_utils.py` - Version comparison using `packaging.version`
- `yaml_utils.py` - YAML validation helpers

**Version Detection (`scripts/version/`):**
- `github.py` - GitHub API integration (releases, tags, metadata)
- `script.py` - PowerShell script execution (30s timeout)
- `url.py` - URL template processing with {version} placeholder replacement
- `web.py` - Fallback web scraping (rarely used)

**Package Handling (`scripts/package/`):**
- `hasher.py` - File download and SHA256 calculation
- `msi.py` - ProductCode extraction using `msitools` (msiinfo command)
- `msix.py` - SignatureSha256 calculation for MSIX packages

**Git Operations (`scripts/git/`):**
- `repo.py` - Fork cloning, branch creation, commit/push operations
- `pr.py` - PR existence checking and creation via `gh` CLI

**Manifest Updates (`scripts/manifest/`):**
- `updater.py` - Smart field update logic (preserves existing fields only)
  - Global version string replacement
  - Multi-architecture hash updates
  - Conditional field updates (ReleaseNotes, ProductCode, etc.)
  - Special handling for edge cases (Microsoft.GameInput DisplayVersion)

### Key Design Patterns

**Auto-Derivation Pattern** (`config.py`):
```python
# Filename: Microsoft.PowerShell.checkver.yaml
packageIdentifier = derive_package_identifier(checkver_path)  # "Microsoft.PowerShell"
manifestPath = derive_manifest_path(packageIdentifier)  # "manifests/m/Microsoft/PowerShell"
```
Detects pattern via GitHub API queries (standard, deep nested, version subdirectory).

**Version Sorting Pattern** (`version_utils.py`):
```python
# Uses packaging.version.parse() for semantic versioning
# Handles 1.2.3, 1.2.3-beta, 1.2.3.0 correctly
latest = get_latest_version(['1.2.3', '1.2.4-beta', '1.2.4'])  # Returns "1.2.4"
```

**Conditional Field Update Pattern** (`manifest/updater.py`):
```python
# Only update fields that exist in old manifest
if 'ReleaseDate' in content:
    content = update_release_date(content)  # Set to current date
if 'ProductCode' in content and product_codes:
    content = update_product_codes(content, product_codes)
```

**Global Version Replacement Strategy**:
1. Extract old version from `PackageVersion:` field
2. Replace ALL occurrences (handles RelativeFilePath, DisplayVersion, URLs)
3. Also replace short versions (7.5.4 when full is 7.5.4.0)
4. Also replace major.minor versions (8.4 → 9.5 for DefaultInstallLocation)

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
- `manifestPath` - Intelligently derived from packageIdentifier with pattern detection:
  - **Standard**: `Microsoft.PowerShell` → `manifests/m/Microsoft/PowerShell`
  - **Deep nested**: `Microsoft.VisualStudio.2022.Community` → `manifests/m/Microsoft/VisualStudio/2022/Community`
  - **Version subdirectory**: `RoyalApps.RoyalTS.7` → `manifests/r/RoyalApps/RoyalTS/7`
  - The system queries GitHub to detect the correct pattern automatically

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

### Release Notes Support

**GitHub-based packages**: ReleaseNotes and ReleaseNotesUrl are automatically fetched from GitHub API (no config needed).

**Script-based packages**: Use `releaseNotesScript` to dynamically fetch release notes:
```yaml
releaseNotesScript: |
  $url = "https://example.com/release-notes-{major}-{minor}-{patch}"
  $resp = Invoke-WebRequest -Uri $url -UseBasicParsing
  # Extract and format release notes
  Write-Output $notes

releaseNotesUrlTemplate: "https://example.com/release-notes-{major}-{minor}-{patch}"
```

**Naming Convention:**
- Config fields with placeholders use `Template` suffix: `installerUrlTemplate`, `releaseNotesUrlTemplate`
- Output fields in version_info.json use resolved values: `installerUrl`, `releaseNotesUrl`

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
The system automatically calculates `manifestPath` from the checkver filename with intelligent pattern detection:
```
Filename: Microsoft.PowerShell.checkver.yaml
  → packageIdentifier: Microsoft.PowerShell
  → manifestPath: manifests/m/Microsoft/PowerShell

Filename: Microsoft.VisualStudio.2022.Community.checkver.yaml
  → packageIdentifier: Microsoft.VisualStudio.2022.Community
  → manifestPath: manifests/m/Microsoft/VisualStudio/2022/Community (deep nested)

Filename: RoyalApps.RoyalTS.7.checkver.yaml
  → packageIdentifier: RoyalApps.RoyalTS.7
  → manifestPath: manifests/r/RoyalApps/RoyalTS/7 (version subdirectory)

Filename: VNGCorp.Zalo.checkver.yaml
  → packageIdentifier: VNGCorp.Zalo
  → manifestPath: manifests/v/VNGCorp/Zalo
```

The detection algorithm:
1. **Deep nested path**: Each dot creates a subdirectory (e.g., `A.B.C.D` → `manifests/a/A/B/C/D`)
2. **Version subdirectory**: Last segment is a number (e.g., `A.B.7` → `manifests/a/A/B/7`)
3. **Standard path**: Publisher + remaining package name (e.g., `A.B` → `manifests/a/A/B`)

The system queries GitHub API to verify which pattern exists before selecting the correct one.

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

## Developer Workflows

### Testing Version Detection Locally
```bash
# Test single package
python3 scripts/check_version.py manifests/Microsoft.PowerShell.checkver.yaml

# Test with output file
python3 scripts/check_version.py manifests/Package.checkver.yaml version_info.json

# View JSON output
cat version_info.json | jq .
```

**Exit codes:**
- `0` = New version detected (version_info.json created)
- `1` = No update needed or check failed

### Adding New Package Checkver

**Step 1:** Inspect existing manifest structure
```bash
# View latest manifest files for a package
curl -s "https://api.github.com/repos/microsoft/winget-pkgs/contents/manifests/r/RustDesk/RustDesk" | jq -r '.[].name'

# Fetch specific version manifest
curl -s "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/manifests/r/RustDesk/RustDesk/1.3.2/RustDesk.RustDesk.installer.yaml"
```

**Step 2:** Identify unusual fields that may need new features:
- Non-standard installer types (MSI, MSIX, portable, etc.)
- Complex ProductCode patterns
- Custom installer switches
- Nested architectures
- Special dependencies

**Step 3:** Create minimal checkver file
```yaml
# manifests/Publisher.Package.checkver.yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Step 4:** Test locally before committing

### Manual Testing Full Pipeline

```bash
# Set required environment variables
export WINGET_PKGS_TOKEN="your_github_token"
export WINGET_FORK_REPO="your_username/winget-pkgs"

# Run full update for a package
python3 scripts/update_manifest.py manifests/Package.checkver.yaml
```

### Common Debugging Commands

```bash
# Check PowerShell version (must be 7.5+)
pwsh --version

# Test PowerShell script manually
pwsh -Command "Write-Output 'Test'"

# Verify msitools installed (for ProductCode extraction)
which msiinfo

# Check GitHub CLI authentication
gh auth status

# View GitHub Actions workflow syntax
gh workflow view "Update WinGet Packages"
```

## Environment

- **Required:** `WINGET_PKGS_TOKEN` (GitHub token with repo + workflow scopes)
- **Optional:** `WINGET_FORK_REPO` (defaults to `{owner}/winget-pkgs`)
- **Runtime:** Ubuntu 24.04, Python 3.11+, PowerShell 7.5+

