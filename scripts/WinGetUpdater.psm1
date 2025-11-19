#Requires -Version 7.5

<#
.SYNOPSIS
    Main PowerShell module for WinGet Package Updater

.DESCRIPTION
    Provides functions for checking package versions and updating WinGet manifests
#>

# Import required modules
using namespace System.Collections.Generic

#region Configuration Functions

function Get-CheckverConfig {
    <#
    .SYNOPSIS
        Load checkver configuration from YAML file

    .PARAMETER CheckverPath
        Path to the checkver YAML file
    #>
    param(
        [Parameter(Mandatory)]
        [string]$CheckverPath
    )

    if (-not (Test-Path $CheckverPath)) {
        throw "Checkver file not found: $CheckverPath"
    }

    # Load YAML using PowerShell-Yaml or ConvertFrom-Yaml
    $content = Get-Content $CheckverPath -Raw
    $config = ConvertFrom-Yaml $content

    # Auto-derive packageIdentifier from filename if not present
    if (-not $config.packageIdentifier) {
        $filename = Split-Path $CheckverPath -Leaf
        $config.packageIdentifier = $filename -replace '\.checkver\.yaml$', ''
    }

    # Auto-derive manifestPath from packageIdentifier if not present
    if (-not $config.manifestPath) {
        $config.manifestPath = Get-ManifestPath $config.packageIdentifier
    }

    return $config
}

function Get-ManifestPath {
    <#
    .SYNOPSIS
        Derive manifest path from package identifier with intelligent detection

    .PARAMETER PackageId
        Package identifier (e.g., Microsoft.PowerShell)
    #>
    param(
        [Parameter(Mandatory)]
        [string]$PackageId
    )

    # Split by first dot to get publisher
    $parts = $PackageId.Split('.', 2)
    if ($parts.Count -ne 2) {
        throw "Invalid package identifier format: $PackageId"
    }

    $publisher = $parts[0]
    $remaining = $parts[1]
    $firstLetter = $publisher[0].ToString().ToLower()

    # Try different path patterns
    $allParts = $PackageId.Split('.')

    # Pattern 1: Deep nested path
    $deepPath = "manifests/$firstLetter/$($allParts -join '/')"

    # Pattern 2: Standard path
    $standardPath = "manifests/$firstLetter/$publisher/$remaining"

    # Pattern 3: Version subdirectory
    $versionedPath = $null
    $remainingParts = $remaining.Split('.')
    if ($remainingParts.Count -ge 2 -and $remainingParts[-1] -match '^\d+$') {
        $packageName = $remainingParts[0..($remainingParts.Count-2)] -join '.'
        $versionDir = $remainingParts[-1]
        $versionedPath = "manifests/$firstLetter/$publisher/$packageName/$versionDir"
    }

    Write-Host "Detecting manifest path pattern for $PackageId..." -ForegroundColor Cyan

    # Check paths in order
    $pathsToCheck = @(
        @{ Type = "deep nested"; Path = $deepPath }
    )

    if ($versionedPath) {
        $pathsToCheck += @{ Type = "versioned"; Path = $versionedPath }
    }

    $pathsToCheck += @{ Type = "standard"; Path = $standardPath }

    foreach ($pathInfo in $pathsToCheck) {
        if (Test-GitHubPath -Path $pathInfo.Path) {
            Write-Host "  ✓ Found $($pathInfo.Type) path: $($pathInfo.Path)" -ForegroundColor Green
            return $pathInfo.Path
        }
    }

    # If nothing exists, prefer deep nested for packages with 3+ parts
    if ($allParts.Count -gt 2) {
        Write-Host "  ⚠ Path doesn't exist yet, using deep nested path for new package" -ForegroundColor Yellow
        return $deepPath
    } else {
        Write-Host "  ⚠ Path doesn't exist yet, using standard path for new package" -ForegroundColor Yellow
        return $standardPath
    }
}

function Test-GitHubPath {
    <#
    .SYNOPSIS
        Check if a path exists in microsoft/winget-pkgs repository
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    try {
        # Try gh CLI first
        $result = gh api "/repos/microsoft/winget-pkgs/contents/$Path" 2>&1
        return $LASTEXITCODE -eq 0
    }
    catch {
        # Fallback to HTTP API
        try {
            $url = "https://api.github.com/repos/microsoft/winget-pkgs/contents/$Path"
            $response = Invoke-RestMethod -Uri $url -Method Get -ErrorAction SilentlyContinue
            return $true
        }
        catch {
            return $false
        }
    }
}

#endregion

#region Version Detection Functions

function Get-LatestWinGetVersion {
    <#
    .SYNOPSIS
        Get the latest version available in microsoft/winget-pkgs
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ManifestPath
    )

    try {
        # Try gh CLI first
        $contents = gh api "/repos/microsoft/winget-pkgs/contents/$ManifestPath" 2>$null | ConvertFrom-Json

        if (-not $contents) {
            # Fallback to HTTP API
            $url = "https://api.github.com/repos/microsoft/winget-pkgs/contents/$ManifestPath"
            $contents = Invoke-RestMethod -Uri $url -ErrorAction SilentlyContinue
        }

        if (-not $contents) {
            return $null
        }

        # Filter for directories only
        $candidateVersions = $contents | Where-Object { $_.type -eq 'dir' } | Select-Object -ExpandProperty name

        if (-not $candidateVersions) {
            return $null
        }

        # Filter out non-version directories by checking for YAML files
        $versions = @()
        foreach ($candidate in $candidateVersions) {
            try {
                $subdirContents = gh api "/repos/microsoft/winget-pkgs/contents/$ManifestPath/$candidate" 2>$null | ConvertFrom-Json

                if (-not $subdirContents) {
                    $subdirUrl = "https://api.github.com/repos/microsoft/winget-pkgs/contents/$ManifestPath/$candidate"
                    $subdirContents = Invoke-RestMethod -Uri $subdirUrl -ErrorAction SilentlyContinue
                }

                if ($subdirContents) {
                    $hasYamlFiles = $subdirContents | Where-Object { $_.type -eq 'file' -and $_.name -like '*.yaml' }
                    if ($hasYamlFiles) {
                        $versions += $candidate
                    }
                }
            }
            catch {
                # If we can't check, assume it might be a version
                $versions += $candidate
            }
        }

        if ($versions.Count -eq 0) {
            return $null
        }

        # Use robust version sorting
        return Get-LatestVersion -Versions $versions
    }
    catch {
        Write-Warning "Could not check microsoft/winget-pkgs: $_"
        return $null
    }
}

function Get-LatestVersion {
    <#
    .SYNOPSIS
        Get the latest version from a list of version strings using semantic versioning
    #>
    param(
        [Parameter(Mandatory)]
        [string[]]$Versions
    )

    if ($Versions.Count -eq 0) {
        throw "Cannot get latest version from empty list"
    }

    # Sort versions using .NET Version class or custom comparison
    $sortedVersions = $Versions | Sort-Object -Property @{
        Expression = {
            try {
                # Try to parse as version
                [version]$_
            }
            catch {
                # Fallback to string comparison
                $_
            }
        }
    } -Descending

    return $sortedVersions[0]
}

function Compare-Version {
    <#
    .SYNOPSIS
        Compare two version strings
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Version1,

        [Parameter(Mandatory)]
        [string]$Version2
    )

    try {
        $v1 = [version]$Version1
        $v2 = [version]$Version2

        if ($v1 -lt $v2) { return -1 }
        elseif ($v1 -gt $v2) { return 1 }
        else { return 0 }
    }
    catch {
        # Fallback to string comparison
        if ($Version1 -lt $Version2) { return -1 }
        elseif ($Version1 -gt $Version2) { return 1 }
        else { return 0 }
    }
}

function Get-LatestVersionFromGitHub {
    <#
    .SYNOPSIS
        Get latest version from GitHub releases
    #>
    param(
        [Parameter(Mandatory)]
        [hashtable]$Config
    )

    $checkver = $Config.checkver
    if ($checkver.type -ne 'github') {
        return $null
    }

    $repo = $checkver.repo
    if (-not $repo) {
        return $null
    }

    try {
        # Fetch latest release
        $release = gh api "/repos/$repo/releases/latest" 2>$null | ConvertFrom-Json

        if (-not $release) {
            # Fallback to HTTP API
            $url = "https://api.github.com/repos/$repo/releases/latest"
            $release = Invoke-RestMethod -Uri $url -ErrorAction Stop
        }

        $version = $release.tag_name -replace '^v', ''

        # Apply appendDotZero if configured
        if ($checkver.appendDotZero -and $version -match '^\d+\.\d+\.\d+$') {
            $version += '.0'
        }

        # Get release metadata
        $metadata = @{
            releaseNotes = $release.body
            releaseNotesUrl = $release.html_url
        }

        return @($version, $metadata)
    }
    catch {
        Write-Warning "Failed to get GitHub release: $_"
        return $null
    }
}

function Get-LatestVersionFromScript {
    <#
    .SYNOPSIS
        Get latest version from PowerShell script
    #>
    param(
        [Parameter(Mandatory)]
        [hashtable]$Config
    )

    $checkver = $Config.checkver
    if ($checkver.type -ne 'script') {
        return $null
    }

    $script = $checkver.script
    if (-not $script) {
        return $null
    }

    try {
        # Execute PowerShell script
        $output = Invoke-Expression $script

        if (-not $output) {
            return $null
        }

        # Apply regex if provided
        $regex = $checkver.regex
        if ($regex) {
            if ($output -match $regex) {
                $version = $matches[0]

                # Apply replace if provided
                if ($checkver.replace) {
                    $replace = $checkver.replace
                    $version = $version -replace $regex, $replace
                }

                # Extract metadata from named groups
                $metadata = @{}
                foreach ($key in $matches.Keys) {
                    if ($key -ne 0 -and $key -is [string]) {
                        $metadata[$key] = $matches[$key]
                    }
                }

                return @($version, $metadata)
            }
        } else {
            return @($output.Trim(), @{})
        }
    }
    catch {
        Write-Warning "Failed to execute version check script: $_"
        return $null
    }

    return $null
}

function Get-InstallerUrl {
    <#
    .SYNOPSIS
        Generate installer URL from template
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Template,

        [Parameter(Mandatory)]
        [string]$Version,

        [hashtable]$Metadata = @{}
    )

    $url = $Template
    $url = $url -replace '\{version\}', $Version

    # Remove trailing .0 for versionShort
    $versionShort = $Version -replace '\.0$', ''
    $url = $url -replace '\{versionShort\}', $versionShort

    # Replace metadata placeholders
    foreach ($key in $Metadata.Keys) {
        $url = $url -replace "\{$key\}", $Metadata[$key]
    }

    return $url
}

function Test-InstallerUrl {
    <#
    .SYNOPSIS
        Verify installer URL is accessible
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Url
    )

    try {
        $response = Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -ErrorAction Stop
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

#endregion

#region Main Functions

function Test-PackageUpdate {
    <#
    .SYNOPSIS
        Check for package updates

    .PARAMETER CheckverPath
        Path to checkver configuration file

    .PARAMETER OutputFile
        Optional path to save version info JSON
    #>
    param(
        [Parameter(Mandatory)]
        [string]$CheckverPath,

        [string]$OutputFile
    )

    try {
        # Load configuration
        $config = Get-CheckverConfig -CheckverPath $CheckverPath
        $packageId = $config.packageIdentifier
        $manifestPath = $config.manifestPath

        Write-Host "Checking for updates: $packageId" -ForegroundColor Cyan

        # Check latest version in microsoft/winget-pkgs
        Write-Host "🔍 Checking latest version in microsoft/winget-pkgs..." -ForegroundColor Cyan
        $wingetLatestVersion = Get-LatestWinGetVersion -ManifestPath $manifestPath

        if ($wingetLatestVersion) {
            Write-Host "   Latest in microsoft/winget-pkgs: $wingetLatestVersion" -ForegroundColor Gray
        } else {
            Write-Host "   No existing version found in microsoft/winget-pkgs" -ForegroundColor Gray
        }

        # Try GitHub-based checkver first
        $versionResult = Get-LatestVersionFromGitHub -Config $config

        # If not GitHub, try script-based checkver
        if (-not $versionResult) {
            $versionResult = Get-LatestVersionFromScript -Config $config
        }

        if (-not $versionResult) {
            Write-Host "Could not determine latest version" -ForegroundColor Red
            return $null
        }

        $latestVersion = $versionResult[0]
        $metadata = $versionResult[1]

        Write-Host "Latest version found: $latestVersion" -ForegroundColor Green

        # Compare versions
        if ($wingetLatestVersion -and $wingetLatestVersion -eq $latestVersion) {
            Write-Host "✅ Version $latestVersion already exists in microsoft/winget-pkgs" -ForegroundColor Green
            Write-Host "⏭️  No update needed, skipping" -ForegroundColor Yellow
            return $null
        }

        # Get installer URLs
        $installerUrlTemplate = $config.installerUrlTemplate
        $installerUrls = @{}
        $primaryUrl = ""

        if ($installerUrlTemplate -is [hashtable]) {
            # Multi-architecture support
            Write-Host "Detected multi-architecture URL templates" -ForegroundColor Cyan
            foreach ($arch in $installerUrlTemplate.Keys) {
                $url = Get-InstallerUrl -Template $installerUrlTemplate[$arch] -Version $latestVersion -Metadata $metadata
                $installerUrls[$arch] = $url
                Write-Host "  $arch : $url" -ForegroundColor Gray
            }
            $primaryUrl = $installerUrls['x64']
            if (-not $primaryUrl) {
                $primaryUrl = $installerUrls.Values | Select-Object -First 1
            }
        } else {
            # Single architecture
            $primaryUrl = Get-InstallerUrl -Template $installerUrlTemplate -Version $latestVersion -Metadata $metadata
            Write-Host "Installer URL: $primaryUrl" -ForegroundColor Gray
        }

        # Build result
        $result = @{
            packageIdentifier = $packageId
            version = $latestVersion
            installerUrl = $primaryUrl
            manifestPath = $manifestPath
        }

        if ($installerUrls.Count -gt 0) {
            $result.installerUrls = $installerUrls
        }

        if ($metadata -and $metadata.Count -gt 0) {
            # Filter out release info fields
            $filteredMetadata = @{}
            foreach ($key in $metadata.Keys) {
                if ($key -notin @('releaseNotes', 'releaseNotesUrl')) {
                    $filteredMetadata[$key] = $metadata[$key]
                }
            }
            if ($filteredMetadata.Count -gt 0) {
                $result.metadata = $filteredMetadata
            }

            # Add release info
            if ($metadata.releaseNotes) {
                $result.releaseNotes = $metadata.releaseNotes
            }
            if ($metadata.releaseNotesUrl) {
                $result.releaseNotesUrl = $metadata.releaseNotesUrl
            }
        }

        # Output result
        $jsonResult = $result | ConvertTo-Json -Depth 10
        Write-Host "`n=== VERSION INFO ===" -ForegroundColor Cyan
        Write-Host $jsonResult

        # Save to file if specified
        if ($OutputFile) {
            $jsonResult | Out-File -FilePath $OutputFile -Encoding utf8
            Write-Host "`nSaved to: $OutputFile" -ForegroundColor Green
        }

        # Set GitHub Actions output
        if ($env:GITHUB_OUTPUT) {
            Add-Content -Path $env:GITHUB_OUTPUT -Value "has_update=true"
            Add-Content -Path $env:GITHUB_OUTPUT -Value "version=$latestVersion"
            Add-Content -Path $env:GITHUB_OUTPUT -Value "package_id=$packageId"
            Add-Content -Path $env:GITHUB_OUTPUT -Value "installer_url=$primaryUrl"
        }

        return $result
    }
    catch {
        Write-Error "Error checking for updates: $_"
        Write-Error $_.ScriptStackTrace

        if ($env:GITHUB_OUTPUT) {
            Add-Content -Path $env:GITHUB_OUTPUT -Value "has_update=false"
        }

        return $null
    }
}

#endregion

# Helper function to convert YAML (basic implementation)
function ConvertFrom-Yaml {
    param([string]$Content)

    # This is a simplified YAML parser for basic checkver configs
    # For production, use powershell-yaml module
    $result = @{}
    $lines = $Content -split "`n"
    $currentKey = $null
    $scriptLines = @()
    $inScript = $false

    foreach ($line in $lines) {
        $trimmed = $line.Trim()

        # Skip comments and empty lines
        if ($trimmed -match '^#' -or [string]::IsNullOrWhiteSpace($trimmed)) {
            continue
        }

        # Handle script blocks
        if ($trimmed -eq 'script: |') {
            $inScript = $true
            $scriptLines = @()
            continue
        }

        if ($inScript) {
            if ($line -match '^  ') {
                $scriptLines += $line.Substring(2)
            } else {
                $result.checkver.script = $scriptLines -join "`n"
                $inScript = $false
            }
        }

        # Parse key-value pairs
        if ($trimmed -match '^(\w+):\s*(.*)$') {
            $key = $matches[1]
            $value = $matches[2]

            if ($value -eq '') {
                # Nested object
                $result[$key] = @{}
                $currentKey = $key
            } else {
                if ($currentKey) {
                    $result[$currentKey][$key] = $value
                } else {
                    $result[$key] = $value
                }
            }
        }
    }

    return $result
}

# Export functions
Export-ModuleMember -Function @(
    'Get-CheckverConfig',
    'Get-ManifestPath',
    'Test-GitHubPath',
    'Get-LatestWinGetVersion',
    'Get-LatestVersion',
    'Compare-Version',
    'Get-LatestVersionFromGitHub',
    'Get-LatestVersionFromScript',
    'Get-InstallerUrl',
    'Test-InstallerUrl',
    'Test-PackageUpdate'
)
