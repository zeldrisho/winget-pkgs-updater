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

**New to this project?** → See [docs/quick-start.md](docs/quick-start.md) for a complete setup guide!

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

See [docs/quick-start.md](docs/quick-start.md) for a quick guide or [docs/contributing.md](docs/contributing.md) for detailed instructions.

## Documentation

### Getting Started
- **[docs/quick-start.md](docs/quick-start.md)** - 5-minute setup guide
- **[docs/contributing.md](docs/contributing.md)** - How to add packages

### Reference
- **[docs/checkver-guide.md](docs/checkver-guide.md)** - Complete checkver configuration reference
- **[docs/architecture.md](docs/architecture.md)** - System architecture and design
- **[docs/development.md](docs/development.md)** - Developer guide and testing

### Additional
- **[manifests/README.md](manifests/README.md)** - Checkver quick reference
- **[.github/workflows/README.md](.github/workflows/README.md)** - Workflow documentation

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

- PowerShell 7.4+
- GitHub CLI (`gh`)
- Git

### PowerShell Modules
- `powershell-yaml` - Automatically installed by workflow

## Features Implemented

✅ Version detection (GitHub API and PowerShell scripts)
✅ Automatic package identifier and manifest path derivation
✅ Installer download and SHA256 calculation
✅ Manifest fetching from microsoft/winget-pkgs
✅ YAML manifest updates with version replacement
✅ Git operations (clone, branch, commit, push)
✅ Pull request creation
✅ ProductCode extraction from MSI files
✅ SignatureSha256 calculation for MSIX packages

## Local Development

### Testing Version Detection

```powershell
# Test a package
pwsh -File scripts/Check-Version.ps1 manifests/Microsoft.PowerShell.checkver.yaml

# Save output to JSON
pwsh -File scripts/Check-Version.ps1 manifests/Package.checkver.yaml version_info.json

# View output
Get-Content version_info.json | ConvertFrom-Json | ConvertTo-Json
```

Exit codes:
- `0` = New version detected
- `1` = No update needed or check failed

### Prerequisites

1. Install PowerShell 7.4+:
   ```bash
   # Windows (winget)
   winget install Microsoft.PowerShell

   # macOS (Homebrew)
   brew install powershell/tap/powershell

   # Linux (see https://aka.ms/install-powershell)
   ```

2. Install GitHub CLI:
   ```bash
   # Windows
   winget install GitHub.cli

   # macOS
   brew install gh

   # Linux
   # See https://github.com/cli/cli#installation
   ```

3. Install PowerShell modules:
   ```powershell
   Install-Module -Name powershell-yaml -Scope CurrentUser
   ```

4. Authenticate GitHub CLI:
   ```bash
   gh auth login
   ```

## Project Structure

```
winget-pkgs-updater/
├── .github/
│   ├── workflows/
│   │   ├── update-packages.yml    # Main workflow
│   │   └── cleanup-branches.yml   # Branch cleanup
│   └── copilot-instructions.md    # AI assistant instructions
├── docs/
│   ├── architecture.md            # System architecture
│   ├── checkver-guide.md          # Checkver configuration
│   ├── development.md             # Developer guide
│   └── contributing.md            # Contributing guide
├── manifests/
│   ├── *.checkver.yaml            # Package configurations
│   └── README.md                  # Checkver basics
├── scripts/
│   ├── WinGetUpdater.psm1         # Main PowerShell module
│   ├── Check-Version.ps1          # Version detection
│   └── Update-Manifest.ps1        # Manifest update
└── README.md                      # This file
```

## Environment Variables

- `GITHUB_TOKEN` or `GH_TOKEN` - GitHub token (required)
- `WINGET_FORK_REPO` - Fork repository (optional, defaults to `{owner}/winget-pkgs`)
- `GITHUB_REPOSITORY_OWNER` - Repository owner (auto-set by GitHub Actions)

## Contributing

See [docs/contributing.md](docs/contributing.md) for guidelines on adding new packages.

## License

GPL-3.0 License - see [LICENSE](LICENSE) file.
