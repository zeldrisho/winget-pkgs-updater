#Requires -Version 7.4

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

    # Custom version comparison that handles any number of components
    $latestVersion = $Versions[0]

    for ($i = 1; $i -lt $Versions.Count; $i++) {
        $current = $Versions[$i]

        # Split versions into numeric components
        $latestParts = @($latestVersion -split '\.' | ForEach-Object { try { [int]$_ } catch { 0 } })
        $currentParts = @($current -split '\.' | ForEach-Object { try { [int]$_ } catch { 0 } })

        # Compare component by component
        $maxLength = [Math]::Max($latestParts.Count, $currentParts.Count)
        $isNewer = $false

        for ($j = 0; $j -lt $maxLength; $j++) {
            $latestVal = if ($j -lt $latestParts.Count) { $latestParts[$j] } else { 0 }
            $currentVal = if ($j -lt $currentParts.Count) { $currentParts[$j] } else { 0 }

            if ($currentVal -gt $latestVal) {
                $isNewer = $true
                break
            }
            elseif ($currentVal -lt $latestVal) {
                break
            }
        }

        if ($isNewer) {
            $latestVersion = $current
        }
    }

    return $latestVersion
}

function Compare-Version {
    <#
    .SYNOPSIS
        Compare two version strings (supports any number of components)
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Version1,

        [Parameter(Mandatory)]
        [string]$Version2
    )

    # Split versions into numeric components
    $v1Parts = @($Version1 -split '\.' | ForEach-Object { try { [int]$_ } catch { 0 } })
    $v2Parts = @($Version2 -split '\.' | ForEach-Object { try { [int]$_ } catch { 0 } })

    # Compare component by component
    $maxLength = [Math]::Max($v1Parts.Count, $v2Parts.Count)

    for ($i = 0; $i -lt $maxLength; $i++) {
        $v1Val = if ($i -lt $v1Parts.Count) { $v1Parts[$i] } else { 0 }
        $v2Val = if ($i -lt $v2Parts.Count) { $v2Parts[$i] } else { 0 }

        if ($v1Val -lt $v2Val) {
            return -1
        }
        elseif ($v1Val -gt $v2Val) {
            return 1
        }
    }

    return 0
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
                # Determine version based on available patterns
                $version = $null

                # Priority 1: Use replace pattern if provided
                if ($checkver.replace) {
                    $replace = $checkver.replace
                    $version = $matches[0] -replace $regex, $replace
                }
                # Priority 2: Use named 'version' group if it exists
                elseif ($matches.ContainsKey('version')) {
                    $version = $matches['version']
                }
                # Priority 3: Use first capture group (numeric index 1)
                elseif ($matches.ContainsKey(1)) {
                    $version = $matches[1]
                }
                # Priority 4: Use full match as fallback
                else {
                    $version = $matches[0]
                }

                # Extract metadata from named groups (excluding 'version')
                $metadata = @{}
                foreach ($key in $matches.Keys) {
                    if ($key -ne 0 -and $key -is [string] -and $key -ne 'version') {
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

function Test-ExistingPullRequest {
    <#
    .SYNOPSIS
        Check if a PR already exists for this package version in microsoft/winget-pkgs

    .DESCRIPTION
        Searches for existing PRs matching the package identifier and version.
        Returns skip status based on PR state:
        - OPEN/MERGED: Skip (already submitted/accepted)
        - CLOSED: Continue (allow retry)
        - Not found: Continue (create new PR)

    .PARAMETER PackageId
        Package identifier to search for

    .PARAMETER Version
        Version number to search for

    .RETURNS
        $true if should skip (PR already exists as OPEN/MERGED), $false otherwise
    #>
    param(
        [Parameter(Mandatory)]
        [string]$PackageId,

        [Parameter(Mandatory)]
        [string]$Version
    )

    try {
        Write-Host "🔍 Checking for existing PRs in microsoft/winget-pkgs..." -ForegroundColor Cyan

        # Search for PRs with package and version in title
        $searchQuery = "$PackageId $Version in:title"
        $prs = gh pr list --repo microsoft/winget-pkgs --search $searchQuery --state all --json number,title,state --limit 10 2>$null | ConvertFrom-Json

        if ($prs -and $prs.Count -gt 0) {
            Write-Host "   Found $($prs.Count) potential matching PR(s)" -ForegroundColor Gray

            foreach ($pr in $prs) {
                # Check if PR title contains both package ID and version
                if ($pr.title -match [regex]::Escape($PackageId) -and $pr.title -match [regex]::Escape($Version)) {
                    if ($pr.state -in @("OPEN", "MERGED")) {
                        Write-Host "   ⚠️  PR #$($pr.number) is already $($pr.state): $($pr.title)" -ForegroundColor Yellow
                        Write-Host "⏭️  Skipping to avoid duplicates" -ForegroundColor Yellow
                        return $true
                    }
                    elseif ($pr.state -eq "CLOSED") {
                        Write-Host "   ℹ️  PR #$($pr.number) was closed: $($pr.title)" -ForegroundColor Gray
                        Write-Host "   ✓ Allowing retry since PR was closed" -ForegroundColor Green
                    }
                }
            }
        }
        else {
            Write-Host "   ✓ No existing PRs found" -ForegroundColor Green
        }

        return $false
    }
    catch {
        Write-Warning "Could not check for existing PRs: $_"
        Write-Warning "Proceeding with caution..."
        return $false
    }
}

#endregion

#region Main Functions

function Test-PackageUpdate {
    <#
    .SYNOPSIS
        Check for package updates using a multi-step verification process

    .DESCRIPTION
        Automated version check workflow:
        1. Checks latest version in microsoft/winget-pkgs repository
        2. Checks latest version from package homepage/source (GitHub releases or custom script)
        3. Compares versions to determine if update is available
        4. Checks for existing PRs to avoid duplicates (OPEN/MERGED = skip, CLOSED = retry)
        5. Returns version info and creates JSON file only if all checks pass
        6. Skips if versions are equal, source version is older, or PR already exists

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
        if ($wingetLatestVersion) {
            $comparison = Compare-Version -Version1 $latestVersion -Version2 $wingetLatestVersion

            if ($comparison -eq 0) {
                Write-Host "✅ Version $latestVersion already exists in microsoft/winget-pkgs" -ForegroundColor Green
                Write-Host "⏭️  No update needed, skipping" -ForegroundColor Yellow
                return $null
            }
            elseif ($comparison -lt 0) {
                Write-Host "⚠️  Source version ($latestVersion) is older than winget-pkgs version ($wingetLatestVersion)" -ForegroundColor Yellow
                Write-Host "⏭️  No update needed, skipping" -ForegroundColor Yellow
                return $null
            }
            else {
                Write-Host "🆕 New version available: $latestVersion (current: $wingetLatestVersion)" -ForegroundColor Green
            }
        }
        else {
            Write-Host "🆕 New package to be added: $latestVersion" -ForegroundColor Green
        }

        # Check for existing PRs before proceeding
        if (Test-ExistingPullRequest -PackageId $packageId -Version $latestVersion) {
            Write-Host "⏭️  Skipping due to existing PR" -ForegroundColor Yellow
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

#region File Operations

function Get-FileSha256 {
    <#
    .SYNOPSIS
        Calculate SHA256 hash of a file
    #>
    param(
        [Parameter(Mandatory)]
        [string]$FilePath
    )

    $hash = Get-FileHash -Path $FilePath -Algorithm SHA256
    return $hash.Hash
}

function Get-WebFile {
    <#
    .SYNOPSIS
        Download a file from URL and detect redirects

    .DESCRIPTION
        Downloads a file and returns information about the final URL after redirects.
        This helps identify vanity URLs that redirect to the actual binary.

    .OUTPUTS
        Returns a hashtable with:
        - Success: Boolean indicating if download succeeded
        - FinalUrl: The final URL after following redirects
        - WasRedirected: Boolean indicating if the URL was redirected
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Url,

        [Parameter(Mandatory)]
        [string]$OutFile
    )

    try {
        Write-Verbose "Downloading: $Url"

        # First, make a request to get the response headers and final URL
        $response = Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -ErrorAction Stop

        # Get the final URL after redirects
        $finalUrl = $response.BaseResponse.ResponseUri.AbsoluteUri
        if (-not $finalUrl) {
            # Fallback for different PowerShell versions
            $finalUrl = $response.BaseResponse.RequestMessage.RequestUri.AbsoluteUri
        }
        if (-not $finalUrl) {
            # If still null, use original URL
            $finalUrl = $Url
        }

        $wasRedirected = $finalUrl -ne $Url

        if ($wasRedirected) {
            Write-Host "  ℹ️  URL redirected:" -ForegroundColor Cyan
            Write-Host "    From: $Url" -ForegroundColor Gray
            Write-Host "    To:   $finalUrl" -ForegroundColor Gray
        }

        return @{
            Success = $true
            FinalUrl = $finalUrl
            WasRedirected = $wasRedirected
        }
    }
    catch {
        Write-Warning "Failed to download $Url : $_"
        return @{
            Success = $false
            FinalUrl = $Url
            WasRedirected = $false
        }
    }
}

function Get-MsiProductCode {
    <#
    .SYNOPSIS
        Extract ProductCode from MSI file

    .PARAMETER FilePath
        Path to MSI file
    #>
    param(
        [Parameter(Mandatory)]
        [string]$FilePath
    )

    if (-not (Test-Path $FilePath)) {
        Write-Warning "MSI file not found: $FilePath"
        return $null
    }

    try {
        # Use Windows Installer COM object
        $installer = New-Object -ComObject WindowsInstaller.Installer
        $database = $installer.GetType().InvokeMember('OpenDatabase', 'InvokeMethod', $null, $installer, @($FilePath, 0))

        # Query ProductCode property
        $query = "SELECT `Value` FROM `Property` WHERE `Property` = 'ProductCode'"
        $view = $database.GetType().InvokeMember('OpenView', 'InvokeMethod', $null, $database, ($query))
        $view.GetType().InvokeMember('Execute', 'InvokeMethod', $null, $view, $null)

        $record = $view.GetType().InvokeMember('Fetch', 'InvokeMethod', $null, $view, $null)

        if ($record) {
            $productCode = $record.GetType().InvokeMember('StringData', 'GetProperty', $null, $record, 1)
            Write-Host "  ✓ Extracted ProductCode: $productCode" -ForegroundColor Green

            # Cleanup COM objects
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($record) | Out-Null
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($view) | Out-Null
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($database) | Out-Null
            [System.Runtime.Interopservices.Marshal]::ReleaseComObject($installer) | Out-Null
            [System.GC]::Collect()

            return $productCode
        }

        # Cleanup if no record found
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($view) | Out-Null
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($database) | Out-Null
        [System.Runtime.Interopservices.Marshal]::ReleaseComObject($installer) | Out-Null
        [System.GC]::Collect()

        return $null
    }
    catch {
        Write-Warning "Failed to extract ProductCode: $_"
        return $null
    }
}

function Get-MsixSignatureSha256 {
    <#
    .SYNOPSIS
        Calculate SignatureSha256 for MSIX/APPX package

    .PARAMETER FilePath
        Path to MSIX/APPX file
    #>
    param(
        [Parameter(Mandatory)]
        [string]$FilePath
    )

    if (-not (Test-Path $FilePath)) {
        Write-Warning "MSIX file not found: $FilePath"
        return $null
    }

    try {
        # Get authenticode signature
        $signature = Get-AuthenticodeSignature -FilePath $FilePath -ErrorAction Stop

        if ($signature.Status -ne 'Valid') {
            Write-Warning "MSIX signature is not valid: $($signature.Status)"
            return $null
        }

        # Calculate SHA256 hash of the signature certificate
        if ($signature.SignerCertificate) {
            $certBytes = $signature.SignerCertificate.GetRawCertData()
            $sha256 = [System.Security.Cryptography.SHA256]::Create()
            $hashBytes = $sha256.ComputeHash($certBytes)
            $signatureSha256 = [System.BitConverter]::ToString($hashBytes) -replace '-', ''

            Write-Host "  ✓ Calculated SignatureSha256: $signatureSha256" -ForegroundColor Green
            return $signatureSha256
        }

        return $null
    }
    catch {
        Write-Warning "Failed to calculate SignatureSha256: $_"
        return $null
    }
}

#endregion

#region Manifest Operations

function Get-UpstreamManifest {
    <#
    .SYNOPSIS
        Fetch manifest files from microsoft/winget-pkgs
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ManifestPath,

        [Parameter(Mandatory)]
        [string]$Version,

        [Parameter(Mandatory)]
        [string]$OutputPath
    )

    try {
        $apiUrl = "https://api.github.com/repos/microsoft/winget-pkgs/contents/$ManifestPath/$Version"
        Write-Host "Fetching manifest from upstream: $apiUrl" -ForegroundColor Cyan

        $files = gh api $apiUrl 2>$null | ConvertFrom-Json

        if (-not $files) {
            # Fallback to HTTP API
            $files = Invoke-RestMethod -Uri $apiUrl -ErrorAction Stop
        }

        New-Item -ItemType Directory -Path $OutputPath -Force | Out-Null

        foreach ($file in $files) {
            if ($file.name -like '*.yaml') {
                $fileUrl = "https://raw.githubusercontent.com/microsoft/winget-pkgs/master/$ManifestPath/$Version/$($file.name)"
                $outFile = Join-Path $OutputPath $file.name

                Write-Host "  Downloading: $($file.name)" -ForegroundColor Gray
                Invoke-WebRequest -Uri $fileUrl -OutFile $outFile -UseBasicParsing | Out-Null
            }
        }

        return $true
    }
    catch {
        Write-Warning "Failed to fetch upstream manifest: $_"
        return $false
    }
}

function Update-ManifestYaml {
    <#
    .SYNOPSIS
        Update YAML manifest with new version and hash
    #>
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,

        [Parameter(Mandatory)]
        [string]$OldVersion,

        [Parameter(Mandatory)]
        [string]$NewVersion,

        [string]$Hash,

        [hashtable]$ArchHashes,

        [string]$ProductCode,

        [string]$SignatureSha256,

        [string]$InstallerUrl
    )

    $content = Get-Content $FilePath -Raw

    # Replace version
    $content = $content -replace "PackageVersion:\s+$([regex]::Escape($OldVersion))", "PackageVersion: $NewVersion"

    # Replace all version occurrences (for URLs, paths, etc.)
    $content = $content -replace [regex]::Escape($OldVersion), $NewVersion

    # Replace InstallerUrl if provided
    if ($InstallerUrl) {
        $escapedUrl = $InstallerUrl.Replace('$', '$$')
        $content = $content -replace "InstallerUrl:\s+.*", "InstallerUrl: $escapedUrl"
    }

    # Replace hash if provided
    if ($Hash) {
        $content = $content -replace "InstallerSha256:\s+[A-Fa-f0-9]{64}", "InstallerSha256: $Hash"
    }

    # Replace ProductCode if provided and exists in manifest
    if ($ProductCode -and $content -match 'ProductCode:') {
        $content = $content -replace "ProductCode:\s+\{[A-Fa-f0-9\-]+\}", "ProductCode: $ProductCode"
        Write-Host "  ✓ Updated ProductCode: $ProductCode" -ForegroundColor Green
    }

    # Replace SignatureSha256 if provided and exists in manifest
    if ($SignatureSha256 -and $content -match 'SignatureSha256:') {
        $content = $content -replace "SignatureSha256:\s+[A-Fa-f0-9]{64}", "SignatureSha256: $SignatureSha256"
        Write-Host "  ✓ Updated SignatureSha256: $SignatureSha256" -ForegroundColor Green
    }

    # Replace architecture-specific hashes if provided
    if ($ArchHashes) {
        foreach ($arch in $ArchHashes.Keys) {
            # This is a simplified implementation
            # Full implementation would need to parse YAML structure
            Write-Verbose "Would update hash for architecture: $arch"
        }
    }

    # Update ReleaseDate to current date if field exists
    if ($content -match 'ReleaseDate:') {
        $today = (Get-Date).ToString("yyyy-MM-dd")
        $content = $content -replace "ReleaseDate:\s+\d{4}-\d{2}-\d{2}", "ReleaseDate: $today"
    }

    Set-Content -Path $FilePath -Value $content -NoNewline
}

function Test-WinGetManifest {
    <#
    .SYNOPSIS
        Validate manifest files using winget validate command

    .DESCRIPTION
        Runs 'winget validate --manifest <path>' to verify manifest files are valid
        before creating a pull request. This catches formatting errors and schema
        violations early.

    .PARAMETER ManifestPath
        Path to the directory containing manifest YAML files

    .RETURNS
        $true if validation passes, $false otherwise
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ManifestPath
    )

    try {
        Write-Host "`nValidating manifest files..." -ForegroundColor Cyan

        # Check if winget is available
        $wingetCmd = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $wingetCmd) {
            Write-Warning "winget command not found. Skipping validation."
            Write-Warning "Install winget from Microsoft Store or https://aka.ms/getwinget"
            return $true  # Don't block PR creation if winget is not available
        }

        # Validate manifest
        Write-Host "  Running: winget validate --manifest `"$ManifestPath`"" -ForegroundColor Gray
        $output = winget validate --manifest $ManifestPath 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Manifest validation passed!" -ForegroundColor Green
            return $true
        }
        else {
            Write-Host "❌ Manifest validation failed!" -ForegroundColor Red
            Write-Host "`nValidation output:" -ForegroundColor Yellow
            Write-Host $output -ForegroundColor Gray
            return $false
        }
    }
    catch {
        Write-Warning "Error during manifest validation: $_"
        Write-Warning "Proceeding without validation..."
        return $true  # Don't block PR creation on validation errors
    }
}

function Test-DuplicateInstallerHash {
    <#
    .SYNOPSIS
        Check if installer hash already exists in microsoft/winget-pkgs

    .DESCRIPTION
        Searches microsoft/winget-pkgs repository for duplicate SHA256 hashes.
        Duplicate hashes may indicate:
        - Same installer reused across versions (common for stable releases)
        - Duplicate package entry (error)
        - Hash collision (extremely rare)

    .PARAMETER Hash
        SHA256 hash to search for

    .PARAMETER PackageId
        Package identifier to exclude from duplicate check (current package)

    .PARAMETER Version
        Version being updated to (for logging purposes)

    .RETURNS
        Object with properties: HasDuplicate (bool), Matches (array)
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Hash,

        [Parameter(Mandatory)]
        [string]$PackageId,

        [Parameter(Mandatory)]
        [string]$Version
    )

    try {
        Write-Host "`nChecking for duplicate installer hashes..." -ForegroundColor Cyan

        # Search for hash in microsoft/winget-pkgs using GitHub code search
        $searchQuery = "$Hash repo:microsoft/winget-pkgs"
        Write-Host "  Searching: $searchQuery" -ForegroundColor Gray

        # Use gh CLI to search (more reliable than API for code search)
        $searchResults = gh search code --repo microsoft/winget-pkgs "$Hash" --json path,repository 2>$null | ConvertFrom-Json

        if (-not $searchResults -or $searchResults.Count -eq 0) {
            Write-Host "  ✓ No duplicate hashes found" -ForegroundColor Green
            return @{
                HasDuplicate = $false
                Matches = @()
            }
        }

        # Parse results to extract package info
        $matches = @()
        foreach ($result in $searchResults) {
            # Path format: manifests/x/Xyz/Package/1.2.3/Xyz.Package.installer.yaml
            if ($result.path -match 'manifests/[^/]+/([^/]+/[^/]+)/([^/]+)/') {
                $foundPackage = $matches[1] -replace '/', '.'
                $foundVersion = $matches[2]

                # Skip if it's the same package (same version is expected duplicate)
                if ($foundPackage -eq $PackageId) {
                    continue
                }

                $matches += @{
                    PackageId = $foundPackage
                    Version = $foundVersion
                    Path = $result.path
                }
            }
        }

        if ($matches.Count -eq 0) {
            Write-Host "  ✓ No duplicate hashes in other packages" -ForegroundColor Green
            return @{
                HasDuplicate = $false
                Matches = @()
            }
        }

        # Found duplicates in other packages - this is unusual
        Write-Host "  ⚠️  Found duplicate hash in $($matches.Count) other package(s):" -ForegroundColor Yellow
        foreach ($match in $matches) {
            Write-Host "     - $($match.PackageId) version $($match.Version)" -ForegroundColor Gray
            Write-Host "       Path: $($match.Path)" -ForegroundColor DarkGray
        }

        Write-Host "`n  ℹ️  This may indicate:" -ForegroundColor Cyan
        Write-Host "     - Same installer used across different packages (vendor bundles)" -ForegroundColor Gray
        Write-Host "     - Possible duplicate entry that should be consolidated" -ForegroundColor Gray
        Write-Host "`n  ⚠️  Consider reviewing before creating PR" -ForegroundColor Yellow

        return @{
            HasDuplicate = $true
            Matches = $matches
        }
    }
    catch {
        Write-Warning "Could not check for duplicate hashes: $_"
        Write-Warning "Proceeding without duplicate check..."
        return @{
            HasDuplicate = $false
            Matches = @()
        }
    }
}

#endregion

#region GitHub API Operations

function Get-GitHubDefaultBranch {
    <#
    .SYNOPSIS
        Get default branch and latest commit SHA from fork repository
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo
    )

    try {
        Write-Host "Fetching default branch from: $ForkRepo" -ForegroundColor Cyan

        $repoOutput = gh api "repos/$ForkRepo" 2>&1

        if ($LASTEXITCODE -ne 0) {
            throw "GitHub API call failed with exit code $LASTEXITCODE. Output: $repoOutput"
        }

        $repo = $repoOutput | ConvertFrom-Json

        if (-not $repo) {
            throw "Failed to fetch repository information"
        }

        $defaultBranch = $repo.default_branch
        Write-Host "  Default branch: $defaultBranch" -ForegroundColor Gray

        # Get the latest commit SHA from the default branch
        $refOutput = gh api "repos/$ForkRepo/git/refs/heads/$defaultBranch" 2>&1

        if ($LASTEXITCODE -ne 0) {
            throw "GitHub API call for branch reference failed with exit code $LASTEXITCODE. Output: $refOutput"
        }

        $ref = $refOutput | ConvertFrom-Json
        $commitSha = $ref.object.sha

        Write-Host "  Latest commit: $commitSha" -ForegroundColor Gray
        Write-Host "✅ Retrieved default branch information" -ForegroundColor Green

        return @{
            Branch = $defaultBranch
            CommitSha = $commitSha
        }
    }
    catch {
        Write-Error "Failed to get default branch: $_"
        return $null
    }
}

function New-GitHubBlob {
    <#
    .SYNOPSIS
        Create a blob in GitHub repository
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$FilePath
    )

    try {
        if (-not (Test-Path $FilePath)) {
            throw "File not found: $FilePath"
        }

        $content = Get-Content -Path $FilePath -Raw
        if ([string]::IsNullOrEmpty($content)) {
            throw "File is empty: $FilePath"
        }

        $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
        $base64 = [Convert]::ToBase64String($bytes)

        $payload = @{
            content = $base64
            encoding = "base64"
        } | ConvertTo-Json

        # Use temp file to avoid pipeline issues
        $tempFile = [System.IO.Path]::GetTempFileName()
        try {
            $payload | Set-Content -Path $tempFile -NoNewline
            $output = gh api "repos/$ForkRepo/git/blobs" --input $tempFile 2>&1

            if ($LASTEXITCODE -ne 0) {
                throw "GitHub API call failed with exit code $LASTEXITCODE. Output: $output"
            }

            $blob = $output | ConvertFrom-Json

            if (-not $blob.sha) {
                throw "Blob creation succeeded but no SHA returned. Response: $output"
            }

            return $blob.sha
        }
        finally {
            Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Error "Failed to create blob for ${FilePath}: $_"
        return $null
    }
}

function Get-GitHubTreeFromCommit {
    <#
    .SYNOPSIS
        Get tree SHA from a commit SHA
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$CommitSha
    )

    try {
        Write-Host "Getting tree SHA from commit..." -ForegroundColor Cyan
        $output = gh api "repos/$ForkRepo/git/commits/$CommitSha" 2>&1

        if ($LASTEXITCODE -ne 0) {
            throw "GitHub API call failed with exit code $LASTEXITCODE. Output: $output"
        }

        $commit = $output | ConvertFrom-Json

        if (-not $commit.tree.sha) {
            throw "Commit retrieved but no tree SHA found. Response: $output"
        }

        Write-Host "  Tree SHA: $($commit.tree.sha)" -ForegroundColor Gray
        return $commit.tree.sha
    }
    catch {
        Write-Error "Failed to get tree SHA from commit: $_"
        return $null
    }
}

function New-GitHubTree {
    <#
    .SYNOPSIS
        Create a tree in GitHub repository with manifest files
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$BaseTreeSha,

        [Parameter(Mandatory)]
        [string]$ManifestPath,

        [Parameter(Mandatory)]
        [string]$Version,

        [Parameter(Mandatory)]
        [hashtable]$FileBlobs
    )

    try {
        Write-Host "Creating git tree..." -ForegroundColor Cyan

        # Validate we have blobs to create
        if ($FileBlobs.Count -eq 0) {
            throw "No file blobs provided. Cannot create an empty tree."
        }

        # Build tree entries for each manifest file
        $treeEntries = @()
        foreach ($fileName in $FileBlobs.Keys) {
            $blobSha = $FileBlobs[$fileName]
            $path = "$ManifestPath/$Version/$fileName"

            $treeEntries += @{
                path = $path
                mode = "100644"
                type = "blob"
                sha = $blobSha
            }

            Write-Host "  Added: $path" -ForegroundColor Gray
        }

        $payload = @{
            base_tree = $BaseTreeSha
            tree = $treeEntries
        } | ConvertTo-Json -Depth 10

        Write-Verbose "Tree payload: $payload"

        # Call GitHub API and capture output properly
        $tempFile = [System.IO.Path]::GetTempFileName()
        try {
            $payload | Set-Content -Path $tempFile -NoNewline
            $output = gh api "repos/$ForkRepo/git/trees" --input $tempFile 2>&1

            if ($LASTEXITCODE -ne 0) {
                throw "GitHub API call failed with exit code $LASTEXITCODE. Output: $output"
            }

            $tree = $output | ConvertFrom-Json

            if (-not $tree.sha) {
                throw "Tree creation succeeded but no SHA returned. Response: $output"
            }

            Write-Host "✅ Tree created: $($tree.sha)" -ForegroundColor Green
            return $tree.sha
        }
        finally {
            Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Error "Failed to create tree: $_"
        return $null
    }
}

function New-GitHubCommit {
    <#
    .SYNOPSIS
        Create a commit in GitHub repository
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$TreeSha,

        [Parameter(Mandatory)]
        [string]$ParentSha,

        [Parameter(Mandatory)]
        [string]$Message
    )

    try {
        Write-Host "Creating commit..." -ForegroundColor Cyan

        $payload = @{
            message = $Message
            tree = $TreeSha
            parents = @($ParentSha)
        } | ConvertTo-Json

        # Use temp file to avoid pipeline issues
        $tempFile = [System.IO.Path]::GetTempFileName()
        try {
            $payload | Set-Content -Path $tempFile -NoNewline
            $output = gh api "repos/$ForkRepo/git/commits" --input $tempFile 2>&1

            if ($LASTEXITCODE -ne 0) {
                throw "GitHub API call failed with exit code $LASTEXITCODE. Output: $output"
            }

            $commit = $output | ConvertFrom-Json

            if (-not $commit.sha) {
                throw "Commit creation succeeded but no SHA returned. Response: $output"
            }

            Write-Host "✅ Commit created: $($commit.sha)" -ForegroundColor Green
            Write-Host "  Message: $Message" -ForegroundColor Gray
            return $commit.sha
        }
        finally {
            Remove-Item -Path $tempFile -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Error "Failed to create commit: $_"
        return $null
    }
}

function New-GitHubBranch {
    <#
    .SYNOPSIS
        Create or update a branch reference in GitHub repository
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$BranchName,

        [Parameter(Mandatory)]
        [string]$CommitSha
    )

    try {
        Write-Host "Creating branch: $BranchName" -ForegroundColor Cyan

        # Try to create new branch first
        $payload = @{
            ref = "refs/heads/$BranchName"
            sha = $CommitSha
        } | ConvertTo-Json

        $result = $payload | gh api "repos/$ForkRepo/git/refs" --input - 2>&1

        if ($LASTEXITCODE -ne 0) {
            # Branch might already exist, try to update it
            Write-Host "  Branch exists, updating..." -ForegroundColor Gray

            $updatePayload = @{
                sha = $CommitSha
                force = $true
            } | ConvertTo-Json

            $result = $updatePayload | gh api "repos/$ForkRepo/git/refs/heads/$BranchName" -X PATCH --input - 2>&1

            if ($LASTEXITCODE -ne 0) {
                throw "Failed to update branch"
            }
        }

        Write-Host "✅ Branch created/updated: $BranchName" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Error "Failed to create/update branch: $_"
        return $false
    }
}

function Publish-ManifestViaAPI {
    <#
    .SYNOPSIS
        Publish manifest files directly via GitHub API without cloning
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$ManifestPath,

        [Parameter(Mandatory)]
        [string]$Version,

        [Parameter(Mandatory)]
        [string]$ManifestDir,

        [Parameter(Mandatory)]
        [string]$PackageId,

        [Parameter(Mandatory)]
        [string]$BranchName
    )

    try {
        # Step 1: Get default branch and base commit
        Write-Host "`nPreparing to publish via GitHub API..." -ForegroundColor Cyan
        $branchInfo = Get-GitHubDefaultBranch -ForkRepo $ForkRepo
        if (-not $branchInfo) {
            throw "Failed to get default branch information"
        }

        $baseCommitSha = $branchInfo.CommitSha

        # Step 2: Create blobs for each manifest file
        Write-Host "`nCreating blobs for manifest files..." -ForegroundColor Cyan
        $manifestFiles = Get-ChildItem -Path $ManifestDir -Filter "*.yaml" -ErrorAction Stop

        if ($manifestFiles.Count -eq 0) {
            throw "No YAML manifest files found in directory: $ManifestDir"
        }

        Write-Host "  Found $($manifestFiles.Count) manifest file(s)" -ForegroundColor Gray

        $fileBlobs = @{}

        foreach ($file in $manifestFiles) {
            Write-Host "  Processing: $($file.Name)" -ForegroundColor Gray
            $blobSha = New-GitHubBlob -ForkRepo $ForkRepo -FilePath $file.FullName

            if (-not $blobSha) {
                throw "Failed to create blob for $($file.Name)"
            }

            $fileBlobs[$file.Name] = $blobSha
            Write-Host "    Blob SHA: $blobSha" -ForegroundColor DarkGray
        }

        Write-Host "✅ Created $($fileBlobs.Count) blobs" -ForegroundColor Green

        # Step 3: Get tree SHA from the base commit
        $baseTreeSha = Get-GitHubTreeFromCommit -ForkRepo $ForkRepo -CommitSha $baseCommitSha
        if (-not $baseTreeSha) {
            throw "Failed to get tree SHA from commit"
        }

        # Step 4: Create tree with the blobs
        $treeSha = New-GitHubTree -ForkRepo $ForkRepo -BaseTreeSha $baseTreeSha -ManifestPath $ManifestPath -Version $Version -FileBlobs $fileBlobs

        if (-not $treeSha) {
            throw "Failed to create tree"
        }

        # Step 5: Create commit
        $commitMessage = "New version: $PackageId version $Version"
        $commitSha = New-GitHubCommit -ForkRepo $ForkRepo -TreeSha $treeSha -ParentSha $baseCommitSha -Message $commitMessage

        if (-not $commitSha) {
            throw "Failed to create commit"
        }

        # Step 6: Create/update branch
        if (-not (New-GitHubBranch -ForkRepo $ForkRepo -BranchName $BranchName -CommitSha $commitSha)) {
            throw "Failed to create branch"
        }

        Write-Host "`n✅ Successfully published manifest via API!" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Error "Failed to publish manifest via API: $_"
        return $false
    }
}

function Publish-ManifestViaGit {
    <#
    .SYNOPSIS
        Publish manifest files using Git CLI (supports GPG signing)
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$ManifestPath,

        [Parameter(Mandatory)]
        [string]$Version,

        [Parameter(Mandatory)]
        [string]$ManifestDir,

        [Parameter(Mandatory)]
        [string]$PackageId,

        [Parameter(Mandatory)]
        [string]$BranchName
    )

    try {
        Write-Host "`nPreparing to publish via Git CLI..." -ForegroundColor Cyan
        
        # Setup Git authentication
        Write-Host "Setting up Git authentication..." -ForegroundColor Cyan
        gh auth setup-git 2>&1 | Out-Null

        # Create temp directory for clone
        $tempDir = Join-Path $env:TEMP "winget-pkgs-git-$(Get-Random)"
        Write-Host "Cloning fork to $tempDir..." -ForegroundColor Cyan
        
        # Use sparse checkout for performance
        $repoUrl = "https://github.com/$ForkRepo.git"
        $cloneOutput = git clone --filter=blob:none --sparse --depth 1 $repoUrl $tempDir 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            throw "Git clone failed: $cloneOutput"
        }

        Push-Location $tempDir

        try {
            # Configure git identity
            git config user.name "WinGet Updater"
            git config user.email "winget-updater@users.noreply.github.com"

            # Configure sparse checkout to include the manifest path
            Write-Host "Configuring sparse checkout for $ManifestPath..." -ForegroundColor Cyan
            git sparse-checkout add $ManifestPath 2>&1 | Out-Null

            # Create and checkout new branch
            Write-Host "Creating branch $BranchName..." -ForegroundColor Cyan
            git checkout -b $BranchName 2>&1 | Out-Null

            # Copy manifest files
            Write-Host "Copying manifest files..." -ForegroundColor Cyan
            $destPath = Join-Path $tempDir $ManifestPath
            
            if (-not (Test-Path $destPath)) {
                New-Item -ItemType Directory -Path $destPath -Force | Out-Null
            }

            Copy-Item "$ManifestDir\*" $destPath -Force

            # Stage changes
            Write-Host "Staging changes..." -ForegroundColor Cyan
            git add . 2>&1 | Out-Null

            # Commit
            $commitMessage = "New version: $PackageId version $Version"
            Write-Host "Committing changes..." -ForegroundColor Cyan
            
            # Check for GPG signing configuration
            $gpgSign = $false
            try {
                $signingKey = git config --get user.signingkey
                if ($signingKey) {
                    $gpgSign = $true
                    Write-Host "  GPG signing enabled (key: $signingKey)" -ForegroundColor Green
                }
            } catch {}

            $commitOutput = git commit -m $commitMessage 2>&1
            
            if ($LASTEXITCODE -ne 0) {
                if ($commitOutput -match "nothing to commit|clean") {
                    Write-Host "⚠️  Nothing to commit (manifest already up to date)" -ForegroundColor Yellow
                    return $true
                }
                throw "Git commit failed: $commitOutput"
            }

            # Push
            Write-Host "Pushing branch..." -ForegroundColor Cyan
            $pushOutput = git push origin $BranchName 2>&1
            
            if ($LASTEXITCODE -ne 0) {
                throw "Git push failed: $pushOutput"
            }

            Write-Host "✅ Successfully published manifest via Git!" -ForegroundColor Green
            return $true
        }
        finally {
            Pop-Location
            Remove-Item $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Write-Error "Failed to publish manifest via Git: $_"
        return $false
    }
}

function New-PullRequest {
    <#
    .SYNOPSIS
        Create pull request to microsoft/winget-pkgs
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkOwner,

        [Parameter(Mandatory)]
        [string]$PackageId,

        [Parameter(Mandatory)]
        [string]$Version,

        [Parameter(Mandatory)]
        [string]$BranchName
    )

    try {
        $title = "New version: $PackageId version $Version"

        # Get workflow run information from environment
        $runNumber = $env:GITHUB_RUN_NUMBER
        $runId = $env:GITHUB_RUN_ID
        $repoName = $env:GITHUB_REPOSITORY
        if (-not $repoName) {
            $repoName = "zeldrisho/winget-pkgs-updater"
        }

        # Automatically search for related open issues on microsoft/winget-pkgs
        Write-Host "🔍 Searching for related issues on microsoft/winget-pkgs..." -ForegroundColor Cyan
        $relatedIssues = @()

        try {
            # Search for issues mentioning the package name and version in title or body
            $searchQuery = "$PackageId $Version in:title,body is:issue is:open"
            $issues = gh issue list --repo microsoft/winget-pkgs --search $searchQuery --json number,title,body --limit 20 2>$null | ConvertFrom-Json

            if ($issues -and $issues.Count -gt 0) {
                Write-Host "   Found $($issues.Count) related issue(s) mentioning package and version" -ForegroundColor Gray

                foreach ($issue in $issues) {
                    Write-Host "   ✓ Will close issue #$($issue.number): $($issue.title)" -ForegroundColor Green
                    $relatedIssues += $issue.number
                }
            }
            else {
                Write-Host "   No related issues found" -ForegroundColor Gray
            }
        }
        catch {
            Write-Warning "Could not search for related issues: $_"
        }

        # Build body with close issues if found
        $closeSection = ""
        if ($relatedIssues.Count -gt 0) {
            $issueRefs = $relatedIssues | ForEach-Object { "Close #$_" }
            $closeSection = ($issueRefs -join "`n") + "`n`n"
        }

        # Create initial body (PR number will be added after creation)
        $body = "${closeSection}Automated by [$repoName](https://github.com/$repoName)"
        if ($runNumber -and $runId) {
            $body += " in workflow run [#$runNumber](https://github.com/$repoName/actions/runs/$runId)"
        }
        $body += "`n"

        Write-Host "Creating pull request..." -ForegroundColor Cyan

        $prUrl = gh pr create `
            --repo microsoft/winget-pkgs `
            --head "$ForkOwner`:$BranchName" `
            --title $title `
            --body $body 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Pull request created successfully!" -ForegroundColor Green
            Write-Host "PR URL: $prUrl" -ForegroundColor Cyan

            # Extract PR number from URL and update body with CodeFlow link
            if ($prUrl -match '/pull/(\d+)') {
                $prNumber = $matches[1]
                $codeflowLink = "`n###### Microsoft Reviewers: [Open in CodeFlow](https://microsoft.github.io/open-pr/?codeflow=https://github.com/microsoft/winget-pkgs/pull/$prNumber)"

                $updatedBody = $body + $codeflowLink

                # Update PR body with CodeFlow link
                gh pr edit $prNumber --repo microsoft/winget-pkgs --body $updatedBody 2>&1 | Out-Null

                if ($LASTEXITCODE -eq 0) {
                    Write-Host "✓ Added CodeFlow link to PR" -ForegroundColor Green
                }
            }

            return $true
        }
        else {
            throw "gh pr create failed with exit code $LASTEXITCODE"
        }
    }
    catch {
        Write-Error "Failed to create pull request: $_"
        return $false
    }
}

#endregion

# Helper function to convert YAML (basic implementation)
function ConvertFrom-Yaml {
    param([string]$Content)

    # Check if powershell-yaml module is available
    if (Get-Module -ListAvailable -Name powershell-yaml) {
        Import-Module powershell-yaml -ErrorAction SilentlyContinue
        if (Get-Command ConvertFrom-Yaml -ErrorAction SilentlyContinue) {
            # Use the module's function
            return & (Get-Command ConvertFrom-Yaml -Module powershell-yaml) -Yaml $Content
        }
    }

    # Fallback to basic YAML parser
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
                if (-not $result.checkver) {
                    $result['checkver'] = @{}
                }
                $result.checkver['script'] = $scriptLines -join "`n"
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
    'Test-ExistingPullRequest',
    'Test-PackageUpdate',
    'Get-FileSha256',
    'Get-WebFile',
    'Get-MsiProductCode',
    'Get-MsixSignatureSha256',
    'Get-UpstreamManifest',
    'Update-ManifestYaml',
    'Test-WinGetManifest',
    'Test-DuplicateInstallerHash',
    'Get-GitHubDefaultBranch',
    'Get-GitHubTreeFromCommit',
    'New-GitHubBlob',
    'New-GitHubTree',
    'New-GitHubCommit',
    'New-GitHubBranch',
    'Publish-ManifestViaAPI',
    'Publish-ManifestViaGit',
    'New-PullRequest'
)
