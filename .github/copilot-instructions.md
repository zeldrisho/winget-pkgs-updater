# WinGet Package Updater - AI Assistant Instructions

This project is a PowerShell-based automation tool that monitors software packages and creates pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when new versions are detected.

## Documentation Structure

All comprehensive documentation has been moved to the `docs/` directory:

- **[docs/architecture.md](../docs/architecture.md)** - System architecture, design patterns, and module structure
- **[docs/checkver-guide.md](../docs/checkver-guide.md)** - Complete checkver configuration reference with examples
- **[docs/development.md](../docs/development.md)** - Developer guide, testing, and debugging
- **[docs/contributing.md](../docs/contributing.md)** - Guide for adding new packages

## Quick Reference

### Technology Stack
- PowerShell 7.5+
- GitHub Actions (Windows runners)
- GitHub CLI (`gh`)
- powershell-yaml module

### Project Structure
```
scripts/
├── WinGetUpdater.psm1         # Main PowerShell module
├── Check-Version.ps1          # Version detection script
└── Update-Manifest.ps1        # Manifest update script (stub)

.github/workflows/
└── update-packages.yml        # Main workflow

manifests/
└── *.checkver.yaml            # Package configurations

docs/
├── architecture.md
├── checkver-guide.md
├── development.md
└── contributing.md
```

### Core Concepts

1. **Auto-Derivation**: Package identifiers and manifest paths are automatically derived from filenames
2. **3-Stage Pipeline**: Version detection → PR gate check → Manifest update
3. **Conditional Updates**: Only updates fields that exist in previous manifest versions
4. **Multi-Architecture Support**: Handles x64, x86, arm64 installers

### When Users Ask...

**"How does the system work?"**
→ Refer to [docs/architecture.md](../docs/architecture.md)

**"How do I add a package?"** or **"How do I write a checkver config?"**
→ Refer to [docs/contributing.md](../docs/contributing.md) and [docs/checkver-guide.md](../docs/checkver-guide.md)

**"How do I test locally?"** or **"How do I debug?"**
→ Refer to [docs/development.md](../docs/development.md)

**"What fields are updated in manifests?"**
→ Refer to [docs/checkver-guide.md](../docs/checkver-guide.md#manifest-update-behavior)

### Important Implementation Notes

- **PowerShell Module**: All core logic is in `scripts/WinGetUpdater.psm1`
- **YAML Parsing**: Uses `powershell-yaml` module (installed automatically by workflow)
- **GitHub API**: Uses `gh` CLI for authenticated requests
- **Version Comparison**: Uses .NET `[version]` type for semantic versioning
- **Exit Codes**: 0 = update found, 1 = no update needed

### Testing Commands

```powershell
# Test version detection
pwsh -File scripts/Check-Version.ps1 manifests/Package.checkver.yaml

# Test with output file
pwsh -File scripts/Check-Version.ps1 manifests/Package.checkver.yaml version_info.json

# View output
Get-Content version_info.json | ConvertFrom-Json | ConvertTo-Json
```

### Key Functions in WinGetUpdater.psm1

- `Get-CheckverConfig` - Load and parse checkver YAML
- `Get-ManifestPath` - Auto-derive manifest path from package ID
- `Get-LatestWinGetVersion` - Query microsoft/winget-pkgs for latest version
- `Get-LatestVersionFromGitHub` - Fetch version from GitHub releases
- `Get-LatestVersionFromScript` - Execute PowerShell version check script
- `Test-PackageUpdate` - Main entry point for version checking

### Common Patterns

**GitHub Release Checkver**:
```yaml
checkver:
  type: github
  repo: owner/repo
  appendDotZero: true

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Script-Based Checkver**:
```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "URL" -UseBasicParsing
    Write-Output $response.Content
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

### Workflow Behavior

1. Runs on Windows runners (for PowerShell compatibility)
2. Installs `powershell-yaml` module
3. Processes all checkver files sequentially
4. Checks for existing PRs before creating new ones
5. Skips packages with OPEN or MERGED PRs
6. Retries packages with CLOSED PRs (if branch deleted)

### Important Notes

- Manifest update script (`Update-Manifest.ps1`) is currently a stub - full implementation TBD
- The system preserves all existing manifest fields and only updates version-related fields
- ProductCode extraction from MSI files requires additional tooling (not yet implemented)
- MSIX SignatureSha256 calculation not yet implemented

For complete details on any topic, refer to the appropriate document in the `docs/` directory.
