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
        $content = $content -replace "InstallerSha256:\s+[A-F0-9]{64}", "InstallerSha256: $Hash"
    }

    # Replace ProductCode if provided and exists in manifest
    if ($ProductCode -and $content -match 'ProductCode:') {
        $content = $content -replace "ProductCode:\s+\{[A-F0-9\-]+\}", "ProductCode: $ProductCode"
        Write-Host "  ✓ Updated ProductCode: $ProductCode" -ForegroundColor Green
    }

    # Replace SignatureSha256 if provided and exists in manifest
    if ($SignatureSha256 -and $content -match 'SignatureSha256:') {
        $content = $content -replace "SignatureSha256:\s+[A-F0-9]{64}", "SignatureSha256: $SignatureSha256"
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

#region Git Operations

function Initialize-GitRepository {
    <#
    .SYNOPSIS
        Clone fork repository using blobless clone for minimal size
    #>
    param(
        [Parameter(Mandatory)]
        [string]$ForkRepo,

        [Parameter(Mandatory)]
        [string]$OutputPath,

        [Parameter(Mandatory)]
        [string]$Token
    )

    try {
        $cloneUrl = "https://x-access-token:$Token@github.com/$ForkRepo.git"
        Write-Host "Cloning repository: $ForkRepo" -ForegroundColor Cyan
        Write-Host "Using blobless clone (--filter=blob:none) for minimal transfer..." -ForegroundColor Gray

        # Configure git for better performance and reliability
        Write-Host "Configuring git for optimized cloning..." -ForegroundColor Gray
        git config --global core.compression 0 2>&1 | Out-Null
        git config --global http.postBuffer 524288000 2>&1 | Out-Null
        git config --global http.version HTTP/1.1 2>&1 | Out-Null

        # Use blobless clone which only downloads trees and commits
        # This is much faster than shallow clone for large repos
        Write-Host "Initializing repository..." -ForegroundColor Cyan
        git clone --filter=blob:none --depth 1 --single-branch --progress $cloneUrl $OutputPath 2>&1 | ForEach-Object {
            $line = $_.ToString()
            if ($line) {
                Write-Host "  $line" -ForegroundColor Gray
            }
        }

        if ($LASTEXITCODE -ne 0) {
            throw "Git clone failed with exit code $LASTEXITCODE"
        }

        # Verify repository was cloned
        if (-not (Test-Path (Join-Path $OutputPath ".git"))) {
            throw "Repository clone completed but .git directory not found"
        }

        Write-Host "✅ Repository cloned successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Error "Failed to clone repository: $_"

        # Cleanup on failure
        if (Test-Path $OutputPath) {
            try {
                Write-Host "Cleaning up failed clone..." -ForegroundColor Yellow
                Remove-Item $OutputPath -Recurse -Force -ErrorAction SilentlyContinue
            }
            catch {
                Write-Warning "Could not cleanup failed clone directory: $_"
            }
        }

        return $false
    }
}

function Set-GitUser {
    <#
    .SYNOPSIS
        Configure git user from GitHub API
    #>
    param(
        [Parameter(Mandatory)]
        [string]$RepoPath
    )

    Push-Location $RepoPath
    try {
        $userInfo = gh api user | ConvertFrom-Json
        $gitName = if ($userInfo.name) { $userInfo.name } else { $userInfo.login }
        $userId = $userInfo.id
        $userLogin = $userInfo.login
        $gitEmail = "$userId+$userLogin@users.noreply.github.com"

        git config user.name $gitName
        git config user.email $gitEmail

        Write-Host "✅ Configured Git: $gitName <$gitEmail>" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Error "Failed to configure git user: $_"
        return $false
    }
    finally {
        Pop-Location
    }
}

function New-GitBranch {
    <#
    .SYNOPSIS
        Create and checkout new branch
    #>
    param(
        [Parameter(Mandatory)]
        [string]$RepoPath,

        [Parameter(Mandatory)]
        [string]$BranchName
    )

    Push-Location $RepoPath
    try {
        git checkout -b $BranchName 2>&1 | Out-Null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Created branch: $BranchName" -ForegroundColor Green
            return $true
        }
        else {
            throw "Failed to create branch"
        }
    }
    catch {
        Write-Error "Failed to create branch: $_"
        return $false
    }
    finally {
        Pop-Location
    }
}

function Publish-GitChanges {
    <#
    .SYNOPSIS
        Commit and push changes
    #>
    param(
        [Parameter(Mandatory)]
        [string]$RepoPath,

        [Parameter(Mandatory)]
        [string]$PackageId,

        [Parameter(Mandatory)]
        [string]$Version,

        [Parameter(Mandatory)]
        [string]$BranchName
    )

    Push-Location $RepoPath
    try {
        # Add all changes
        git add . 2>&1 | Out-Null

        # Create commit
        $commitMessage = "New version: $PackageId version $Version"
        git commit -m $commitMessage 2>&1 | Out-Null

        if ($LASTEXITCODE -ne 0) {
            throw "Git commit failed"
        }

        Write-Host "✅ Created commit: $commitMessage" -ForegroundColor Green

        # Push with retries
        $maxRetries = 4
        $retryCount = 0
        $delay = 2

        while ($retryCount -lt $maxRetries) {
            Write-Host "Pushing to remote (attempt $($retryCount + 1)/$maxRetries)..." -ForegroundColor Cyan

            git push -u origin $BranchName 2>&1 | Out-Null

            if ($LASTEXITCODE -eq 0) {
                Write-Host "✅ Push successful!" -ForegroundColor Green
                return $true
            }

            $retryCount++
            if ($retryCount -lt $maxRetries) {
                Write-Host "⚠️  Push failed, retrying in ${delay}s..." -ForegroundColor Yellow
                Start-Sleep -Seconds $delay
                $delay *= 2
            }
        }

        throw "Push failed after $maxRetries attempts"
    }
    catch {
        Write-Error "Failed to publish changes: $_"
        return $false
    }
    finally {
        Pop-Location
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

This PR was created automatically by the WinGet Package Updater.
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
    'Initialize-GitRepository',
    'Set-GitUser',
    'New-GitBranch',
    'Publish-GitChanges',
    'New-PullRequest'
)
