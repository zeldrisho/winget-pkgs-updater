# WinGet Package Updater

Automated tool to check for new package versions and create pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).

## Features

- 🔄 Automatic version detection using PowerShell scripts or GitHub API
- 🤖 Auto-derived package identifiers and manifest paths from filenames
- 📦 Smart manifest updates (preserves existing fields, updates only what's needed)
- 🔐 Automatic hash calculation (InstallerSha256, SignatureSha256, ProductCode)
- 🔍 Smart PR management (skip OPEN/MERGED, retry CLOSED)
- 📝 GitHub metadata auto-fetch (ReleaseNotes, ReleaseNotesUrl)
- 🎯 Multi-architecture support with MSIX/MSI handling
- 🤖 GitHub Actions integration (scheduled or manual)

## Quick Setup

### 1. Fork Repositories

- Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)
- Fork this repository

### 2. Create GitHub Token

1. Go to [GitHub Settings → Developer settings → Tokens (classic)](https://github.com/settings/tokens)
2. Generate new token with scopes: `repo`, `workflow`
3. Copy the token

### 3. Add Secrets

In your forked repository:

- Go to Settings → Secrets and variables → Actions
- Create secret: `WINGET_PKGS_TOKEN` = your token (required)
- Create secret: `WINGET_FORK_REPO` = your fork repository in format `username/winget-pkgs` (optional, defaults to `{GITHUB_REPOSITORY_OWNER}/winget-pkgs`)

### 4. Run Workflow

- Go to Actions → Update WinGet Packages → Run workflow

## Adding Packages

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guide on adding new packages.

## Documentation

- [CONTRIBUTING.md](CONTRIBUTING.md) - How to add packages
- [manifests/README.md](manifests/README.md) - Checkver configuration

## How It Works

### 3-Stage Pipeline

#### Stage 1: Version Detection
1. **Auto-derive identifiers** - Extract packageIdentifier from filename
2. **Query winget-pkgs** - Find latest published version via GitHub API
3. **Run version check** - Execute PowerShell script or GitHub API query
4. **Compare versions** - Exit with new version info if update available

#### Stage 2: PR Gate Check
5. **Search existing PRs** - Query microsoft/winget-pkgs for matching PRs
   - **OPEN/MERGED** → Skip (already submitted/accepted)
   - **CLOSED** → Check fork branch status
     - Branch exists → Skip (avoid duplicate)
     - Branch deleted → Continue (allow retry)

#### Stage 3: Manifest Update
6. **Clone fork** - Clone your winget-pkgs fork
7. **Fetch manifests** - Copy latest version folder from upstream
8. **Download installers** - Download files for hash calculation
9. **Calculate hashes** - InstallerSha256 + SignatureSha256 (MSIX) + ProductCode (MSI)
10. **Update manifests** - Smart field updates:
    - **Always updated**: PackageVersion, InstallerSha256, InstallerUrl
    - **Conditionally updated**: ProductCode, ReleaseDate, ReleaseNotes (if exist in old manifest)
    - **Preserved**: All other fields (Publisher, License, Tags, etc.)
11. **Create PR** - Push to fork and open PR to microsoft/winget-pkgs

## PR Management

| PR State | Behavior |
|----------|----------|
| 🟢 OPEN | Skip - Already submitted |
| 🟣 MERGED | Skip - Already in winget-pkgs |
| ⚪ CLOSED | Create new PR - Allow retry |

## Requirements

- Python 3.11+
- PowerShell 7.5+
- GitHub CLI (`gh`)
- Dependencies: `pip install -r scripts/requirements.txt`

## License

GPL-3.0 License - see [LICENSE](LICENSE) file.
