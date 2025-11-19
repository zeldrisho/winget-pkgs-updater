#Requires -Version 7.5

<#
.SYNOPSIS
    Update WinGet manifest with new version

.DESCRIPTION
    Fetches existing manifest from microsoft/winget-pkgs, updates it with new version and hashes,
    and creates a pull request

.PARAMETER CheckverPath
    Path to checkver config file

.PARAMETER PackageId
    Package identifier (if Version is also provided)

.PARAMETER Version
    Version number (if PackageId is provided)

.PARAMETER NoP

R
    Update manifests without creating PR (for testing)

.PARAMETER ForkPath
    Path to existing fork clone (for testing)

.EXAMPLE
    ./Update-Manifest.ps1 manifests/Microsoft.PowerShell.checkver.yaml Microsoft.PowerShell 7.5.4.0
#>

param(
    [Parameter(Mandatory, Position=0)]
    [string]$CheckverPath,

    [Parameter(Position=1)]
    [string]$PackageId,

    [Parameter(Position=2)]
    [string]$Version,

    [switch]$NoPR,

    [string]$ForkPath
)

$ErrorActionPreference = 'Stop'

Write-Host "WinGet Manifest Updater - PowerShell Edition" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

try {
    # Load checkver config
    $content = Get-Content $CheckverPath -Raw
    $config = ConvertFrom-Yaml $content

    # Auto-derive packageIdentifier
    $filename = Split-Path $CheckverPath -Leaf
    $derivedPackageId = $filename -replace '\.checkver\.yaml$', ''

    if (-not $PackageId) {
        $PackageId = $derivedPackageId
    }

    if (-not $Version) {
        Write-Error "Version parameter is required"
        exit 1
    }

    Write-Host "`nPackage: $PackageId" -ForegroundColor Green
    Write-Host "Version: $Version" -ForegroundColor Green

    # Get environment variables
    $forkRepo = $env:WINGET_FORK_REPO
    if (-not $forkRepo) {
        $forkOwner = $env:GITHUB_REPOSITORY_OWNER
        if (-not $forkOwner) {
            $forkOwner = 'zeldrisho'
        }
        $forkRepo = "$forkOwner/winget-pkgs"
    }

    $token = $env:GITHUB_TOKEN
    if (-not $token) {
        $token = $env:GH_TOKEN
    }

    if (-not $token) {
        throw "GITHUB_TOKEN or GH_TOKEN environment variable not set"
    }

    Write-Host "`nFork Repository: $forkRepo" -ForegroundColor Cyan

    # Get installer URLs
    $installerUrlTemplate = $config.installerUrlTemplate

    # Generate installer URLs
    $installerUrls = @{}
    $primaryUrl = ""

    if ($installerUrlTemplate -is [hashtable]) {
        Write-Host "`nMulti-architecture package detected" -ForegroundColor Cyan
        foreach ($arch in $installerUrlTemplate.Keys) {
            $url = $installerUrlTemplate[$arch] -replace '\{version\}', $Version
            $url = $url -replace '\{versionShort\}', ($Version -replace '\.0$', '')
            $installerUrls[$arch] = $url
            Write-Host "  $arch : $url" -ForegroundColor Gray
        }
        $primaryUrl = $installerUrls['x64']
        if (-not $primaryUrl) {
            $primaryUrl = $installerUrls.Values | Select-Object -First 1
        }
    } else {
        $primaryUrl = $installerUrlTemplate -replace '\{version\}', $Version
        $primaryUrl = $primaryUrl -replace '\{versionShort\}', ($Version -replace '\.0$', '')
        Write-Host "`nInstaller URL: $primaryUrl" -ForegroundColor Gray
    }

    # Create branch name
    $branchName = "$PackageId-$Version"

    # Clone fork or use existing path
    $tempDir = $null
    if ($ForkPath) {
        $repoDir = $ForkPath
        Write-Host "`nUsing existing fork at: $repoDir" -ForegroundColor Cyan
    } else {
        $tempDir = New-Item -ItemType Directory -Path (Join-Path $env:TEMP "winget-pkgs-$(Get-Random)")
        $repoDir = Join-Path $tempDir "winget-pkgs"

        Write-Host "`nCloning fork repository..." -ForegroundColor Cyan
        git clone "https://x-access-token:$token@github.com/$forkRepo.git" $repoDir
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to clone repository"
        }

        Set-Location $repoDir
    }

    # Configure git user
    Write-Host "`nConfiguring Git user..." -ForegroundColor Cyan
    $userInfo = gh api user | ConvertFrom-Json
    $gitName = if ($userInfo.name) { $userInfo.name } else { $userInfo.login }
    $userId = $userInfo.id
    $userLogin = $userInfo.login
    $gitEmail = "$userId+$userLogin@users.noreply.github.com"

    git config user.name $gitName
    git config user.email $gitEmail
    Write-Host "✅ Configured Git: $gitName <$gitEmail>" -ForegroundColor Green

    # Create branch
    Write-Host "`nCreating branch: $branchName" -ForegroundColor Cyan
    git checkout -b $branchName
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to create branch"
    }

    Write-Host "`n⚠️  Note: Full manifest update logic not yet implemented in PowerShell version" -ForegroundColor Yellow
    Write-Host "This is a stub implementation. The Python version had complex manifest update logic." -ForegroundColor Yellow
    Write-Host "For production use, implement the following:" -ForegroundColor Yellow
    Write-Host "  1. Download installer and calculate SHA256" -ForegroundColor Gray
    Write-Host "  2. Extract ProductCode from MSI files" -ForegroundColor Gray
    Write-Host "  3. Calculate SignatureSha256 for MSIX packages" -ForegroundColor Gray
    Write-Host "  4. Copy latest manifest folder from upstream" -ForegroundColor Gray
    Write-Host "  5. Update manifest YAML files with new version and hashes" -ForegroundColor Gray
    Write-Host "  6. Commit, push, and create PR" -ForegroundColor Gray

    # Cleanup
    if ($tempDir) {
        Set-Location $PSScriptRoot
        Remove-Item $tempDir -Recurse -Force
    }

    Write-Host "`n✅ Script completed" -ForegroundColor Green
}
catch {
    Write-Error "Error updating manifest: $_"
    Write-Error $_.ScriptStackTrace
    exit 1
}
