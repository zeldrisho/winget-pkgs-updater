# Development Guide

Guide for developers working on WinGet Package Updater.

## Prerequisites

- **PowerShell 7.4+** - Download from [PowerShell releases](https://github.com/PowerShell/PowerShell/releases)
- **GitHub CLI (gh)** - Install from [GitHub CLI](https://cli.github.com/)
- **Git** - For version control
- **powershell-yaml** module - Installed automatically by workflows

## Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/winget-pkgs-updater.git
   cd winget-pkgs-updater
   ```

2. Install PowerShell modules:
   ```powershell
   Install-Module -Name powershell-yaml -Scope CurrentUser
   ```

3. Authenticate with GitHub CLI:
   ```bash
   gh auth login
   ```

## Testing Version Detection

Test a single package locally:

```powershell
# Basic test
pwsh -File scripts/Check-Version.ps1 manifests/Microsoft.PowerShell.checkver.yaml

# Save output to JSON
pwsh -File scripts/Check-Version.ps1 manifests/Package.checkver.yaml version_info.json

# View JSON output
Get-Content version_info.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Exit codes**:
- `0` - New version detected
- `1` - No update needed or check failed

## Testing PowerShell Scripts

Test PowerShell script blocks from checkver configs:

```powershell
# Test script execution
$script = @"
`$response = Invoke-WebRequest -Uri 'https://example.com' -UseBasicParsing
Write-Output `$response.Content
"@

Invoke-Expression $script
```

## Module Development

The main module is `scripts/WinGetUpdater.psm1`. To test changes:

```powershell
# Import module
Import-Module ./scripts/WinGetUpdater.psm1 -Force

# Test functions
$config = Get-CheckverConfig -CheckverPath "manifests/Package.checkver.yaml"
$version = Get-LatestVersionFromGitHub -Config $config
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
│   ├── development.md             # This file
│   └── contributing.md            # Contributing guide
├── manifests/
│   └── *.checkver.yaml            # Package configurations
├── scripts/
│   ├── WinGetUpdater.psm1         # Main PowerShell module
│   ├── Check-Version.ps1          # Version detection script
│   └── Update-Manifest.ps1        # Manifest update script
└── README.md                      # Project readme
```

## Common Development Tasks

### Adding a New Function to the Module

1. Edit `scripts/WinGetUpdater.psm1`
2. Add your function in the appropriate region
3. Export the function at the end:
   ```powershell
   Export-ModuleMember -Function @(
       'Existing-Function',
       'Your-New-Function'
   )
   ```

### Testing GitHub Actions Locally

Use `act` to test workflows locally:

```bash
# Install act
# https://github.com/nektos/act

# Run workflow
act -j update
```

### Debugging PowerShell Scripts

Enable verbose output:

```powershell
$VerbosePreference = 'Continue'
pwsh -File scripts/Check-Version.ps1 manifests/Package.checkver.yaml
```

Use breakpoints:

```powershell
# In your script
Set-PSBreakpoint -Line 42 -Script ./scripts/Check-Version.ps1
```

## Code Style Guidelines

### PowerShell

- Use **approved verbs** for function names: `Get-`, `Set-`, `Test-`, `New-`
- Use **PascalCase** for function names
- Use **camelCase** for variables
- Include **comment-based help** for all functions
- Use **Write-Host** with colors for user-facing messages
- Use **Write-Verbose** for debug information
- Use **Write-Warning** for warnings
- Use **Write-Error** for errors

**Example**:
```powershell
function Get-PackageVersion {
    <#
    .SYNOPSIS
        Get the latest version of a package

    .PARAMETER PackageName
        Name of the package
    #>
    param(
        [Parameter(Mandatory)]
        [string]$PackageName
    )

    Write-Verbose "Checking version for $PackageName"

    # Implementation
}
```

### YAML Checkver Files

- **Minimal configs** - Only include required fields
- **No comments** in production checkver files
- **Use spaces, not tabs**
- **2-space indentation**

## Testing Checklist

Before submitting changes:

- [ ] Test locally with at least 2 different checkver files
- [ ] Verify exit codes are correct (0 for success, 1 for no update)
- [ ] Check that JSON output is valid
- [ ] Test both GitHub and script-based checkver types
- [ ] Test multi-architecture packages
- [ ] Run PowerShell script analyzer:
  ```powershell
  Invoke-ScriptAnalyzer -Path scripts/ -Recurse
  ```

## Common Issues

### PowerShell Version Mismatch

Ensure you're using PowerShell 7.4+:
```powershell
$PSVersionTable.PSVersion
```

If using an older version, some features may not work.

### GitHub API Rate Limiting

GitHub API has rate limits:
- **Unauthenticated**: 60 requests/hour
- **Authenticated**: 5,000 requests/hour

Use `gh auth login` to authenticate.

### Module Not Loading

Force reload the module:
```powershell
Remove-Module WinGetUpdater -ErrorAction SilentlyContinue
Import-Module ./scripts/WinGetUpdater.psm1 -Force
```

### YAML Parsing Errors

Ensure powershell-yaml is installed:
```powershell
Get-Module -ListAvailable powershell-yaml

# If not installed
Install-Module -Name powershell-yaml -Force -Scope CurrentUser
```

## Useful Commands

```powershell
# Check PowerShell version
pwsh --version

# List installed modules
Get-Module -ListAvailable

# Test if GitHub CLI is working
gh auth status

# View API rate limit
gh api rate_limit

# Test regex patterns
'version 1.2.3' -match '(\d+\.\d+\.\d+)'
$matches[1]  # Should output '1.2.3'

# Test JSON output
Get-Content version_info.json | Test-Json
```

## Resources

- [PowerShell Documentation](https://docs.microsoft.com/en-us/powershell/)
- [GitHub CLI Manual](https://cli.github.com/manual/)
- [WinGet Package Repository](https://github.com/microsoft/winget-pkgs)
- [YAML Specification](https://yaml.org/spec/)
