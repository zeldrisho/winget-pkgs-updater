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

**New to this project?** → See **[docs/quick-start.md](docs/quick-start.md)** for complete 5-minute setup guide!

**TL;DR**: Fork repos → Add `WINGET_PKGS_TOKEN` secret → Create `.checkver.yaml` files → Run workflow

## Adding Packages

See **[docs/contributing.md](docs/contributing.md)** for detailed instructions on adding new packages.

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

#### Stage 1: Version Detection & Validation
1. **Auto-derive identifiers** - Extract packageIdentifier from filename
2. **Query winget-pkgs** - Find latest published version via GitHub API
3. **Run version check** - Execute PowerShell script or GitHub API query
4. **Compare versions** - Determine if update is available
5. **Check existing PRs** - Query microsoft/winget-pkgs for matching PRs
   - **OPEN/MERGED** → Skip (already submitted/accepted)
   - **CLOSED** → Continue (allow retry)
   - **Not found** → Continue (create new PR)
6. **Output version_info.json** - Only if all checks pass

#### Stage 2: Manifest Update
7. **Fetch manifests** - Download latest version folder from upstream via API
8. **Download installers** - Download files for hash calculation
9. **Calculate hashes** - InstallerSha256 + SignatureSha256 (MSIX) + ProductCode (MSI)
10. **Update manifests** - Smart field updates:
    - **Always updated**: PackageVersion, InstallerSha256, InstallerUrl
    - **Conditionally updated**: ProductCode, ReleaseDate, ReleaseNotes (if exist in old manifest)
    - **Preserved**: All other fields (Publisher, License, Tags, etc.)
11. **Validate manifests** - Run `winget validate --manifest` to verify correctness

#### Stage 3: Publish
12. **Publish via API** - Create commit and branch directly using GitHub API (no cloning)
13. **Create PR** - Open PR from fork branch to microsoft/winget-pkgs

## PR Management

| PR State | Behavior |
|----------|----------|
| 🟢 OPEN | Skip - Already submitted |
| 🟣 MERGED | Skip - Already in winget-pkgs |
| ⚪ CLOSED | Create new PR - Allow retry |

## Requirements

- PowerShell 7.4+
- GitHub CLI (`gh`)

### PowerShell Modules
- `powershell-yaml` - Automatically installed by workflow

## Features Implemented

✅ Version detection (GitHub API and PowerShell scripts)
✅ Automatic package identifier and manifest path derivation
✅ Installer download and SHA256 calculation
✅ Manifest fetching from microsoft/winget-pkgs
✅ YAML manifest updates with version replacement
✅ Manifest validation using `winget validate` before PR creation
✅ GitHub API-based commit creation (no repository cloning)
✅ Pull request creation with automatic issue detection and closing
✅ ProductCode extraction from MSI files
✅ SignatureSha256 calculation for MSIX packages

## Local Development

See **[docs/development.md](docs/development.md)** for complete local development guide including:

- Testing version detection
- Manifest validation
- Prerequisites and setup
- Debugging tips

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
