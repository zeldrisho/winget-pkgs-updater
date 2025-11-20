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
        Download a file from URL
    #>
    param(
        [Parameter(Mandatory)]
        [string]$Url,

        [Parameter(Mandatory)]
        [string]$OutFile
    )

    try {
        Write-Verbose "Downloading: $Url"
        Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing -ErrorAction Stop
        return $true
    }
    catch {
        Write-Warning "Failed to download $Url : $_"
        return $false
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

        [string]$SignatureSha256
    )

    $content = Get-Content $FilePath -Raw

    # Replace version
    $content = $content -replace "PackageVersion:\s+$([regex]::Escape($OldVersion))", "PackageVersion: $NewVersion"

    # Replace all version occurrences (for URLs, paths, etc.)
    $content = $content -replace [regex]::Escape($OldVersion), $NewVersion

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

        $repo = gh api "repos/$ForkRepo" 2>&1 | ConvertFrom-Json

        if (-not $repo) {
            throw "Failed to fetch repository information"
        }

        $defaultBranch = $repo.default_branch
        Write-Host "  Default branch: $defaultBranch" -ForegroundColor Gray

        # Get the latest commit SHA from the default branch
        $ref = gh api "repos/$ForkRepo/git/refs/heads/$defaultBranch" 2>&1 | ConvertFrom-Json
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
        $content = Get-Content -Path $FilePath -Raw
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($content)
        $base64 = [Convert]::ToBase64String($bytes)

        $payload = @{
            content = $base64
            encoding = "base64"
        } | ConvertTo-Json

        $blob = $payload | gh api "repos/$ForkRepo/git/blobs" --input - 2>&1 | ConvertFrom-Json

        if (-not $blob.sha) {
            throw "Failed to create blob"
        }

        return $blob.sha
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
        $commit = gh api "repos/$ForkRepo/git/commits/$CommitSha" 2>&1 | ConvertFrom-Json

        if (-not $commit.tree.sha) {
            throw "Failed to get tree SHA from commit"
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

        $tree = $payload | gh api "repos/$ForkRepo/git/trees" --input - 2>&1 | ConvertFrom-Json

        if (-not $tree.sha) {
            throw "Failed to create tree"
        }

        Write-Host "✅ Tree created: $($tree.sha)" -ForegroundColor Green
        return $tree.sha
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

        $commit = $payload | gh api "repos/$ForkRepo/git/commits" --input - 2>&1 | ConvertFrom-Json

        if (-not $commit.sha) {
            throw "Failed to create commit"
        }

        Write-Host "✅ Commit created: $($commit.sha)" -ForegroundColor Green
        Write-Host "  Message: $Message" -ForegroundColor Gray
        return $commit.sha
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
        $manifestFiles = Get-ChildItem -Path $ManifestDir -Filter "*.yaml"
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
        $body = @"
## Update Information

- **Package**: $PackageId
- **Version**: $Version
- **Submitted by**: Automated WinGet Package Updater
- **Automation**: https://github.com/zeldrisho/winget-pkgs-updater

This PR was created automatically by the [WinGet Package Updater](https://github.com/zeldrisho/winget-pkgs-updater).
"@

        Write-Host "Creating pull request..." -ForegroundColor Cyan

        $pr = gh pr create `
            --repo microsoft/winget-pkgs `
            --head "$ForkOwner`:$BranchName" `
            --title $title `
            --body $body 2>&1

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Pull request created successfully!" -ForegroundColor Green
            Write-Host "PR URL: $pr" -ForegroundColor Cyan
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
    'Test-PackageUpdate',
    'Get-FileSha256',
    'Get-WebFile',
    'Get-MsiProductCode',
    'Get-MsixSignatureSha256',
    'Get-UpstreamManifest',
    'Update-ManifestYaml',
    'Get-GitHubDefaultBranch',
    'Get-GitHubTreeFromCommit',
    'New-GitHubBlob',
    'New-GitHubTree',
    'New-GitHubCommit',
    'New-GitHubBranch',
    'Publish-ManifestViaAPI',
    'New-PullRequest'
)
