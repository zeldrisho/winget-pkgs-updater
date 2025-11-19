# Architecture Overview

WinGet Package Updater is a PowerShell-based automation tool that monitors software packages and creates pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when new versions are detected.

## Technology Stack

- **PowerShell 7.5+** - Main automation language
- **GitHub Actions** - CI/CD platform
- **GitHub CLI (gh)** - API interactions
- **powershell-yaml** - YAML configuration parsing

## 3-Stage Pipeline

The updater runs in three stages on GitHub Actions:

### Stage 1: Version Detection

1. Query microsoft/winget-pkgs API to find latest published version
2. Execute version check (PowerShell script or GitHub API)
3. Compare versions - exit 0 if new version found, exit 1 if same
4. **Output**: `version_info.json` containing package metadata

**Supports**:
- GitHub API integration for releases
- Custom PowerShell scripts for version detection
- Metadata extraction via named regex groups

### Stage 2: PR Gate Check

Prevents duplicate pull requests by checking:

1. Search microsoft/winget-pkgs for existing PRs matching package+version
   - **OPEN or MERGED** → Skip (already submitted/accepted)
   - **CLOSED** → Check if branch exists on fork
     - Branch exists → Skip (avoid duplicate PR)
     - Branch deleted → Continue (can retry)

**Purpose**: Respects upstream decisions and prevents spam

### Stage 3: Manifest Update

1. Clone fork of microsoft/winget-pkgs
2. Fetch existing manifests for latest version
3. Download installers and calculate SHA256 hashes (supports multi-arch)
4. Extract ProductCode from MSI files (if applicable)
5. Copy manifest folder and apply updates
6. Create branch, commit, push to fork, open PR

**Strategy**: Copy entire manifest folder → selective field updates → global version string replacement

## Module Structure

### Core Scripts

- `scripts/WinGetUpdater.psm1` - Main PowerShell module
  - Configuration loading (YAML parsing, auto-derivation)
  - Version detection (GitHub API, script execution)
  - Version comparison and sorting

- `scripts/Check-Version.ps1` - Entry point for version detection (Stage 1)
- `scripts/Update-Manifest.ps1` - Entry point for manifest updates (Stage 3)

### Key Design Patterns

#### Auto-Derivation Pattern

```powershell
# Filename: Microsoft.PowerShell.checkver.yaml
# → packageIdentifier: Microsoft.PowerShell
# → manifestPath: manifests/m/Microsoft/PowerShell

# Filename: Microsoft.VisualStudio.2022.Community.checkver.yaml
# → packageIdentifier: Microsoft.VisualStudio.2022.Community
# → manifestPath: manifests/m/Microsoft/VisualStudio/2022/Community (deep nested)
```

The system queries GitHub API to detect the correct manifest path pattern automatically.

#### Version Sorting Pattern

Uses .NET `[version]` type for semantic versioning:
- Handles 1.2.3, 1.2.3-beta, 1.2.3.0 correctly
- Falls back to string comparison for non-standard versions

#### Conditional Field Update Pattern

Only updates fields that exist in the old manifest:
```powershell
if ($manifest.ReleaseDate) {
    $manifest.ReleaseDate = (Get-Date).ToString("yyyy-MM-dd")
}
```

## Workflow Orchestration

GitHub Actions workflow:
1. Runs on schedule (every 4 hours) or manual dispatch
2. Uses Windows runners for PowerShell compatibility
3. Installs powershell-yaml module
4. Processes all checkver files in sequence
5. Creates PRs for packages with updates

## Environment Variables

- **GITHUB_TOKEN** or **GH_TOKEN** - GitHub token with repo + workflow scopes (required)
- **WINGET_FORK_REPO** - Fork repository (optional, defaults to `{owner}/winget-pkgs`)
- **GITHUB_REPOSITORY_OWNER** - Repository owner (auto-set by GitHub Actions)

## Security Considerations

- Uses GitHub CLI for authenticated API calls
- Tokens stored as GitHub Secrets
- No sensitive data in logs
- Branch naming prevents conflicts: `{PackageId}-{Version}`
