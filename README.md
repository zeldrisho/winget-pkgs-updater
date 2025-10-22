# WinGet Package Updater

Automated tool to check for new package versions and create pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).

## Features

- 🔄 Automatic version detection using PowerShell scripts or GitHub API
- 📦 Full manifest updates (Version, URL, SHA256, SignatureSha256, ReleaseDate)
- 🔍 Smart PR management (skip OPEN/MERGED, retry CLOSED)
- 🎯 MSIX support with automatic signature calculation
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

1. **Check Version** - Runs PowerShell script to detect latest version
2. **Check Existing PR** - Searches for OPEN/MERGED PRs (skip if found)
3. **Download Installer** - Downloads installer file (if needed)
4. **Calculate Hashes** - InstallerSha256 + SignatureSha256 (for MSIX)
5. **Clone Fork** - Clones your winget-pkgs fork
6. **Update Manifests** - Replaces all version occurrences + updates hashes
7. **Create PR** - Creates PR to microsoft/winget-pkgs

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
