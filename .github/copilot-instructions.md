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

## Checkver Configuration

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

**Standard Placeholders:**
- `{version}` - Full version (e.g., 2.3.12.0)
- `{versionShort}` - Version without trailing .0

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

**Multi-Architecture URLs:**
```yaml
installerUrlTemplate:
  x64: "https://example.com/{version}-win64.zip"
  arm64: "https://example.com/{version}-arm64.zip"
```

**Fetching from Raw Sources:**
For packages where version info comes from raw text files (not installers):
```yaml
# Example: Sysinternals Suite uses static download URLs
# Version is determined by documentation date
checkver:
  script: |
    $response = Invoke-WebRequest -Uri "https://raw.githubusercontent.com/..." -UseBasicParsing
    Write-Output $response.Content
  regex: "ms\\.date: (\\d{2})/(\\d{2})/(\\d{4})"
  replace: "${3}.${1}.${2}"

installerUrlTemplate:
  x64: "https://download.example.com/files/Package.zip"
  # URL doesn't change, but version metadata does
```
The updater fetches manifests from microsoft/winget-pkgs and updates version fields only.

## Key Concepts

- **Global String Replacement:** update_manifest.py replaces ALL occurrences of old version with new version
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

