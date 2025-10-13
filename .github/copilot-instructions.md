# WinGet Package Updater - AI Coding Agent Instructions

## Project Overview

This is an automated tool that monitors software packages and creates pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when new versions are detected. The system runs on GitHub Actions, checking versions via PowerShell scripts and managing the entire PR lifecycle.

## Architecture

### Three-Layer System

1. **Version Detection** (`scripts/check_version.py`)
   - Executes PowerShell scripts from checkver configs to scrape version info
   - Supports multiple detection methods: GitHub API, web scraping, redirect following
   - Outputs version info JSON for next stage

2. **Manifest Update** (`scripts/update_manifest.py`)
   - Fetches existing manifests from microsoft/winget-pkgs
   - Downloads installers to calculate SHA256 hashes
   - Special handling: MSIX files require SignatureSha256 calculation via PowerShell
   - Performs **global version string replacement** across all manifest files

3. **PR Management**
   - Smart PR detection: skip if OPEN/MERGED, retry if CLOSED
   - Creates branch in user's winget-pkgs fork
   - Submits PR to upstream microsoft/winget-pkgs

## Critical Patterns

### Checkver Configuration (manifests/*.checkver.yaml)

**Structure:**
```yaml
packageIdentifier: Publisher.Package
manifestPath: manifests/{first-letter}/{publisher}/{package}  # lowercase first letter
checkver:
  type: script
  script: |
    # PowerShell code that outputs version string to stdout
  regex: "([\\d\\.]+)"
installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

**Path Convention:** The `manifestPath` must match microsoft/winget-pkgs structure:
- `Seelen.SeelenUI` → `manifests/s/Seelen/SeelenUI`
- `VNGCorp.Zalo` → `manifests/v/VNGCorp/Zalo`

**Version Template Variables:**
- `{version}` - Full version (e.g., 2.3.12.0)
- `{versionShort}` - Version without trailing .0 (e.g., 2.3.12)

### Manifest Update Strategy

**Global String Replacement:** `update_manifest.py` replaces ALL occurrences of the old version string across all manifest files (version, installer, locale manifests). This handles:
- `PackageVersion: 1.0.0` → `PackageVersion: 2.0.0`
- URLs: `installer/v1.0.0/app.exe` → `installer/v2.0.0/app.exe`
- Display names: `App 1.0.0` → `App 2.0.0`

**Hash Calculation:**
- Standard installers: SHA256 of file
- MSIX/APPX: SHA256 + SignatureSha256 (extracted via PowerShell's Get-AuthenticodeSignature)

### PowerShell Integration

**Why PowerShell:** Many version detection patterns require Windows-specific APIs or complex HTTP handling (redirects, headers). All scripts run via `pwsh` (PowerShell 7.5+).

**Common Patterns:**
```powershell
# GitHub releases
Invoke-RestMethod -Uri "https://api.github.com/repos/owner/repo/releases/latest"

# Following redirects
Invoke-WebRequest -MaximumRedirection 0 -ErrorAction SilentlyContinue

# MSIX signature extraction
Get-AuthenticodeSignature $packagePath
```

## Development Workflows

### Testing New Packages

```bash
# 1. Create checkver config in manifests/
python3 scripts/check_version.py manifests/YourPackage.checkver.yaml

# 2. Test full update (requires WINGET_PKGS_TOKEN)
python3 scripts/update_manifest.py --checkver manifests/YourPackage.checkver.yaml
```

### Local Dependencies

```bash
pip install -r scripts/requirements.txt  # Python: requests, PyYAML, beautifulsoup4
sudo apt-get install -y powershell      # PowerShell 7.5+
gh auth login                            # GitHub CLI for PR operations
```

### Workflow Triggers

- **Scheduled:** Every 6 hours (`update-packages.yml`)
- **Manual:** workflow_dispatch with optional package filter
- **PR Testing:** Validates checkver configs on PR (`test-manifest-checker.yml`)

## Key Files

- **manifests/*.checkver.yaml** - Package version detection configs
- **scripts/check_version.py** - Version detection orchestrator (PowerShell executor)
- **scripts/update_manifest.py** - Manifest updater + PR creator (500+ lines, handles entire lifecycle)
- **.github/workflows/update-packages.yml** - Main automation workflow

## Environment Requirements

- **Secrets:** 
  - `WINGET_PKGS_TOKEN` - GitHub token with `repo` + `workflow` scopes (required)
  - `WINGET_FORK_REPO` - Fork repository in format `username/winget-pkgs` (optional, defaults to `{GITHUB_REPOSITORY_OWNER}/winget-pkgs`)
- **Runtime:** Ubuntu 24.04, Python 3.11+, PowerShell 7.5+, GitHub CLI
- **Fork:** User must have forked microsoft/winget-pkgs

## Anti-Patterns

❌ Don't edit manifests directly - they're fetched from microsoft/winget-pkgs
❌ Don't use regex for partial version replacement - global string replace is safer
❌ Don't skip PR existence check - causes duplicate PRs
❌ Don't forget SignatureSha256 for MSIX installers - microsoft/winget-pkgs validates this

## Common Failure Points

1. **PowerShell script returns empty** - Check timeout (30s limit), network issues, API rate limits
2. **SignatureSha256 missing** - MSIX files require signature extraction via PowerShell
3. **Version already exists** - Workflow checks microsoft/winget-pkgs before creating PR
4. **Fork not found** - Verify WINGET_PKGS_TOKEN has access to user's fork and WINGET_FORK_REPO is correct format (username/winget-pkgs)
5. **Git fetch upstream fails** - Ensure fork exists and token has proper permissions
