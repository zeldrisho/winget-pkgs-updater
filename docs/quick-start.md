# Quick Start Guide

Get started with WinGet Package Updater in minutes.

## Prerequisites

- PowerShell 7.5+
- GitHub CLI (`gh`)
- Git

## Setup (5 minutes)

### 1. Fork Repositories

Fork these two repositories:
- [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)
- [This repository](https://github.com/zeldrisho/winget-pkgs-updater)

### 2. Create GitHub Token

1. Go to [GitHub Settings → Developer settings → Tokens (classic)](https://github.com/settings/tokens)
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`
4. Click "Generate token" and **copy it**

### 3. Configure Secrets

In your forked `winget-pkgs-updater` repository:

1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add secret: `WINGET_PKGS_TOKEN` = your token from step 2
4. (Optional) Add secret: `WINGET_FORK_REPO` = `yourusername/winget-pkgs`

### 4. Enable Workflow

1. Go to **Actions** tab in your fork
2. Click "I understand my workflows, go ahead and enable them"

### 5. Run Your First Update

1. Go to **Actions** → **Update WinGet Packages**
2. Click **Run workflow** → **Run workflow**
3. Watch it check for updates!

## Adding Your First Package

### Step 1: Choose a Package

Pick a software package that:
- Is hosted on GitHub (easiest)
- Has releases with downloadable installers
- Already exists in [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)

### Step 2: Create Checkver File

Create `manifests/{Publisher}.{Package}.checkver.yaml`:

```yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/installer.exe"
```

**Example** (Microsoft PowerShell):
```yaml
checkver:
  type: github
  repo: PowerShell/PowerShell
  appendDotZero: true

installerUrlTemplate:
  x64: "https://github.com/PowerShell/PowerShell/releases/download/v{versionShort}/PowerShell-{versionShort}-win-x64.msi"
```

### Step 3: Test Locally

```powershell
# Install PowerShell module
Install-Module -Name powershell-yaml -Scope CurrentUser

# Authenticate GitHub CLI
gh auth login

# Test version detection
pwsh -File scripts/Check-Version.ps1 manifests/YourPackage.checkver.yaml

# Check output
Get-Content version_info.json | ConvertFrom-Json | ConvertTo-Json
```

### Step 4: Commit and Push

```bash
git add manifests/YourPackage.checkver.yaml
git commit -m "Add checkver for YourPackage"
git push
```

The workflow will automatically start checking for updates!

## Common Patterns

### GitHub Release (Simple)

```yaml
checkver:
  type: github
  repo: rustdesk/rustdesk

installerUrlTemplate: "https://github.com/rustdesk/rustdesk/releases/download/{version}/rustdesk-{version}-x86_64.exe"
```

### GitHub Release (Multi-Architecture)

```yaml
checkver:
  type: github
  repo: PowerShell/PowerShell

installerUrlTemplate:
  x64: "https://github.com/PowerShell/PowerShell/releases/download/v{version}/PowerShell-{version}-win-x64.msi"
  x86: "https://github.com/PowerShell/PowerShell/releases/download/v{version}/PowerShell-{version}-win-x86.msi"
  arm64: "https://github.com/PowerShell/PowerShell/releases/download/v{version}/PowerShell-{version}-win-arm64.msi"
```

### GitHub with Version Transform

```yaml
checkver:
  type: github
  repo: PowerShell/PowerShell
  appendDotZero: true  # v7.5.4 → 7.5.4.0

installerUrlTemplate:
  x64: "https://github.com/PowerShell/PowerShell/releases/download/v{versionShort}/PowerShell-{versionShort}-win-x64.msi"
```

### Custom Script

```yaml
checkver:
  type: script
  script: |
    $url = "https://example.com/downloads"
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing
    if ($response.Content -match 'Version (\d+\.\d+\.\d+)') {
      Write-Output $matches[1]
    }
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/downloads/v{version}/installer.msi"
```

## Workflow Behavior

The automated workflow:

1. ✅ Runs every 4 hours (or manually)
2. 🔍 Checks all packages for new versions
3. ⏭️ Skips packages with existing OPEN/MERGED PRs
4. 📥 Downloads new installers and calculates SHA256
5. 📝 Updates manifest files
6. 🚀 Creates pull requests to microsoft/winget-pkgs

## Troubleshooting

### "No update needed"
- Package is already at latest version ✅
- Or version check failed ❌

### "Failed to create PR"
- Check that `WINGET_PKGS_TOKEN` is set correctly
- Verify token has `repo` and `workflow` scopes
- Check that your fork exists

### "Version not detected"
- Test PowerShell script: `pwsh -Command "your script here"`
- Verify regex pattern matches the output
- Check that script writes to stdout (use `Write-Output`)

## Next Steps

- Read [docs/checkver-guide.md](checkver-guide.md) for advanced configuration
- Read [docs/contributing.md](contributing.md) for detailed guidelines
- Read [docs/development.md](development.md) for local development
- Browse existing checkver files in `manifests/` for examples

## Getting Help

- 📖 Check [docs/](../docs/) for detailed documentation
- 🐛 [Open an issue](https://github.com/zeldrisho/winget-pkgs-updater/issues) for bugs
- 💬 [Start a discussion](https://github.com/zeldrisho/winget-pkgs-updater/discussions) for questions
