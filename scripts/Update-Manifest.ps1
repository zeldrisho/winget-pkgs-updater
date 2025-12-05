#Requires -Version 7.4

<#
.SYNOPSIS
    Update WinGet manifest with new version

.DESCRIPTION
    Fetches existing manifest from microsoft/winget-pkgs, updates it with new version and hashes,
    and creates a pull request using GitHub API (no repository cloning required)

.PARAMETER CheckverPath
    Path to checkver config file

.PARAMETER PackageId
    Package identifier (if Version is also provided)

.PARAMETER Version
    Version number (if PackageId is provided)

.PARAMETER NoPR
    Update manifests without creating PR (for testing)

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

    [switch]$NoPR
)

$ErrorActionPreference = 'Stop'
$VerbosePreference = 'Continue'

# Import module
Import-Module "$PSScriptRoot/WinGetUpdater.psm1" -Force

Write-Host "`n======================================" -ForegroundColor Cyan
Write-Host "WinGet Manifest Updater - PowerShell" -ForegroundColor Cyan
Write-Host "======================================`n" -ForegroundColor Cyan

try {
    # Load checkver config
    Write-Host "Loading checkver config..." -ForegroundColor Cyan
    $config = Get-CheckverConfig -CheckverPath $CheckverPath

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

    $manifestPath = $config.manifestPath

    Write-Host "Package ID: $PackageId" -ForegroundColor Green
    Write-Host "Version: $Version" -ForegroundColor Green
    Write-Host "Manifest Path: $manifestPath`n" -ForegroundColor Green

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

    Write-Host "Fork Repository: $forkRepo`n" -ForegroundColor Cyan

    # Try to load metadata from version_info.json if available
    $metadata = @{}
    if (Test-Path "version_info.json") {
        try {
            $versionInfo = Get-Content "version_info.json" -Raw | ConvertFrom-Json
            if ($versionInfo.metadata) {
                $metadata = @{}
                foreach ($property in $versionInfo.metadata.PSObject.Properties) {
                    $metadata[$property.Name] = $property.Value
                }
                Write-Host "Loaded metadata from version_info.json:" -ForegroundColor Cyan
                foreach ($key in $metadata.Keys) {
                    Write-Host "  $key = $($metadata[$key])" -ForegroundColor Gray
                }
                Write-Host ""
            }
        }
        catch {
            Write-Warning "Could not load metadata from version_info.json: $_"
        }
    }

    # Get installer URL
    $installerUrlTemplate = $config.installerUrlTemplate

    if ($installerUrlTemplate -is [hashtable]) {
        # Multi-architecture
        Write-Host "Multi-architecture package detected" -ForegroundColor Cyan
        $installerUrls = @{}
        foreach ($arch in $installerUrlTemplate.Keys) {
            $url = Get-InstallerUrl -Template $installerUrlTemplate[$arch] -Version $Version -Metadata $metadata
            $installerUrls[$arch] = $url
            Write-Host "  $arch : $url" -ForegroundColor Gray
        }
        $primaryUrl = $installerUrls['x64']
        if (-not $primaryUrl) {
            $primaryUrl = $installerUrls.Values | Select-Object -First 1
        }
    } else {
        # Single architecture
        Write-Verbose "Template: $installerUrlTemplate"
        Write-Verbose "Version: $Version"
        Write-Verbose "Metadata keys: $($metadata.Keys -join ', ')"
        $primaryUrl = Get-InstallerUrl -Template $installerUrlTemplate -Version $Version -Metadata $metadata
        $installerUrls = $null
        Write-Host "Installer URL: $primaryUrl" -ForegroundColor Gray
        
        # Verify placeholder was replaced
        if ($primaryUrl -match '\{[^\}]+\}') {
            Write-Warning "URL still contains placeholders: $primaryUrl"
            Write-Warning "This indicates Get-InstallerUrl did not replace all placeholders"
        }

    }

    # Get latest version from winget-pkgs to use as template
    Write-Host "`nFinding latest version in microsoft/winget-pkgs..." -ForegroundColor Cyan
    $latestVersion = Get-LatestWinGetVersion -ManifestPath $manifestPath

    if (-not $latestVersion) {
        Write-Error "Could not find existing version in microsoft/winget-pkgs"
        Write-Host "This package may not exist yet in the repository." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Latest version in upstream: $latestVersion" -ForegroundColor Green

    # Create branch name
    $branchName = "$PackageId-$Version"
    Write-Host "`nBranch name: $branchName" -ForegroundColor Cyan

    # Fetch template manifest from upstream
    $templateDir = Join-Path $env:TEMP "manifest-template-$(Get-Random)"
    Write-Host "`nFetching template manifest from upstream..." -ForegroundColor Cyan

    if (-not (Get-UpstreamManifest -ManifestPath $manifestPath -Version $latestVersion -OutputPath $templateDir)) {
        throw "Failed to fetch template manifest"
    }

    # Create new version directory for manifests
    $newVersionDir = Join-Path $env:TEMP "manifest-new-$(Get-Random)"
    Write-Host "`nCreating new version directory..." -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $newVersionDir -Force | Out-Null

    # Download installer(s) and calculate hash(es)
    Write-Host "`nDownloading installer(s) to calculate hash..." -ForegroundColor Cyan

    $installerHash = $null
    $archHashes = @{}
    $archProductCodes = @{}
    $archSignatures = @{}
    $productCode = $null
    $signatureSha256 = $null
    $finalInstallerUrl = $primaryUrl

    if ($installerUrls) {
        # Multi-architecture: Download each installer and calculate separate hashes
        Write-Host "Multi-architecture package - downloading all installers..." -ForegroundColor Cyan
        
        foreach ($arch in $installerUrls.Keys) {
            $url = $installerUrls[$arch]
            Write-Host "`n  Processing $arch architecture..." -ForegroundColor Cyan
            Write-Host "    URL: $url" -ForegroundColor Gray
            
            # Detect installer type from URL
            $installerExtension = [System.IO.Path]::GetExtension($url).ToLower()
            if ($installerExtension -eq '') {
                # Try to detect from URL pattern
                if ($url -match '\.msi($|\?)') { $installerExtension = '.msi' }
                elseif ($url -match '\.msix($|\?)') { $installerExtension = '.msix' }
                elseif ($url -match '\.appx($|\?)') { $installerExtension = '.appx' }
                else { $installerExtension = '.exe' }
            }

            $tempInstaller = Join-Path $env:TEMP "installer-$arch-$(Get-Random)$installerExtension"
            $downloadResult = Get-WebFile -Url $url -OutFile $tempInstaller

            if ($downloadResult.Success) {
                # Calculate hash for this architecture
                $hash = Get-FileSha256 -FilePath $tempInstaller
                $archHashes[$arch] = $hash
                Write-Host "    ✅ SHA256: $hash" -ForegroundColor Green

                # Extract ProductCode for MSI installers
                if ($installerExtension -eq '.msi') {
                    $archProductCode = Get-MsiProductCode -FilePath $tempInstaller
                    if ($archProductCode) {
                        $archProductCodes[$arch] = $archProductCode
                        Write-Host "    ✅ ProductCode: $archProductCode" -ForegroundColor Green
                    }
                }

                # Extract SignatureSha256 for MSIX/APPX packages
                if ($installerExtension -in @('.msix', '.appx')) {
                    $archSig = Get-MsixSignatureSha256 -FilePath $tempInstaller
                    if ($archSig) {
                        $archSignatures[$arch] = $archSig
                        Write-Host "    ✅ SignatureSha256: $archSig" -ForegroundColor Green
                    }
                }

                Remove-Item $tempInstaller -Force
            } else {
                Write-Warning "    ❌ Could not download installer for $arch"
            }
        }

        # Use x64 hash as primary hash for single-hash manifests (backward compatibility)
        if ($archHashes.ContainsKey('x64')) {
            $installerHash = $archHashes['x64']
        } elseif ($archHashes.Count -gt 0) {
            $installerHash = $archHashes.Values | Select-Object -First 1
        }

        Write-Host "`n📊 Multi-architecture download summary:" -ForegroundColor Cyan
        Write-Host "  Total hashes collected: $($archHashes.Count)" -ForegroundColor Gray
        foreach ($arch in $archHashes.Keys) {
            Write-Host "    $arch : $($archHashes[$arch])" -ForegroundColor Gray
        }

        if ($archHashes.Count -eq 0) {
            Write-Error "❌ Failed to download any installers for multi-architecture package!"
            Write-Host "Expected architectures: $($installerUrls.Keys -join ', ')" -ForegroundColor Yellow
            exit 1
        }

    } else {
        # Single architecture: Download one installer
        # Detect installer type from URL
        $installerExtension = [System.IO.Path]::GetExtension($primaryUrl).ToLower()
        if ($installerExtension -eq '') {
            # Try to detect from URL pattern
            if ($primaryUrl -match '\.msi($|\?)') { $installerExtension = '.msi' }
            elseif ($primaryUrl -match '\.msix($|\?)') { $installerExtension = '.msix' }
            elseif ($primaryUrl -match '\.appx($|\?)') { $installerExtension = '.appx' }
            else { $installerExtension = '.exe' }
        }

        $tempInstaller = Join-Path $env:TEMP "installer-$(Get-Random)$installerExtension"
        $downloadResult = Get-WebFile -Url $primaryUrl -OutFile $tempInstaller

        if ($downloadResult.Success) {
            # Store the final URL after redirects
            $finalInstallerUrl = $downloadResult.FinalUrl

            # Warn if URL was redirected (vanity URL detected)
            if ($downloadResult.WasRedirected) {
                Write-Host "`n⚠️  Warning: Vanity URL detected!" -ForegroundColor Yellow
                Write-Host "   The installer URL redirects to a different location." -ForegroundColor Yellow
                Write-Host "   This may cause SHA256 hash mismatch issues in WinGet." -ForegroundColor Yellow
                Write-Host "   Original URL: $primaryUrl" -ForegroundColor Gray
                Write-Host "   Final URL:    $finalInstallerUrl" -ForegroundColor Gray
                Write-Host "   Consider updating the checkver config to use the final URL directly.`n" -ForegroundColor Yellow
            }

            # Calculate installer hash
            $installerHash = Get-FileSha256 -FilePath $tempInstaller
            Write-Host "✅ Calculated SHA256: $installerHash" -ForegroundColor Green

            # Extract ProductCode for MSI installers
            if ($installerExtension -eq '.msi') {
                Write-Host "`nExtracting ProductCode from MSI..." -ForegroundColor Cyan
                $productCode = Get-MsiProductCode -FilePath $tempInstaller
            }

            # Extract SignatureSha256 for MSIX/APPX packages
            if ($installerExtension -in @('.msix', '.appx')) {
                Write-Host "`nCalculating SignatureSha256 for MSIX..." -ForegroundColor Cyan
                $signatureSha256 = Get-MsixSignatureSha256 -FilePath $tempInstaller
            }

            Remove-Item $tempInstaller -Force
        } else {
            Write-Error "❌ Failed to download installer for single-architecture package!"
            Write-Host "URL: $primaryUrl" -ForegroundColor Yellow
            exit 1
        }
    }

    # Copy and update manifest files
    Write-Host "`nUpdating manifest files..." -ForegroundColor Cyan
    $manifestFiles = Get-ChildItem -Path $templateDir -Filter "*.yaml"

    foreach ($file in $manifestFiles) {
        $destFile = Join-Path $newVersionDir $file.Name
        Copy-Item $file.FullName $destFile -Force

        Write-Host "  Updating: $($file.Name)" -ForegroundColor Gray

        # Update manifest with all extracted data
        $updateParams = @{
            FilePath = $destFile
            OldVersion = $latestVersion
            NewVersion = $Version
        }

        # Add architecture-specific hashes if available
        if ($archHashes.Count -gt 0) {
            Write-Host "    ℹ️  Applying architecture-specific hashes: $($archHashes.Count) architectures" -ForegroundColor Cyan
            foreach ($arch in $archHashes.Keys) {
                Write-Host "      $arch : $($archHashes[$arch])" -ForegroundColor Gray
            }
            $updateParams['ArchHashes'] = $archHashes
            # Also add arch-specific ProductCodes and SignatureSha256 if available
            if ($archProductCodes.Count -gt 0) {
                $updateParams['ArchProductCodes'] = $archProductCodes
            }
            if ($archSignatures.Count -gt 0) {
                $updateParams['ArchSignatures'] = $archSignatures
            }
        } else {
            # Single architecture - use legacy single hash parameter
            if ($installerHash) {
                Write-Host "    ℹ️  Applying single-architecture hash: $installerHash" -ForegroundColor Cyan
                $updateParams['Hash'] = $installerHash
            } else {
                Write-Warning "    ⚠️  No installer hash available - manifest will not be updated with new hash!"
            }
            if ($productCode) {
                $updateParams['ProductCode'] = $productCode
            }
            if ($signatureSha256) {
                $updateParams['SignatureSha256'] = $signatureSha256
            }
        }

        if (-not $installerUrls) {
            $updateParams['InstallerUrl'] = $primaryUrl
        }

        Update-ManifestYaml @updateParams
    }

    # Cleanup template directory
    Remove-Item $templateDir -Recurse -Force

    # Validate manifest files before publishing
    if (-not (Test-WinGetManifest -ManifestPath $newVersionDir)) {
        Write-Error "Manifest validation failed. Please review the errors above."
        Write-Host "`nManifest directory: $newVersionDir" -ForegroundColor Yellow
        Write-Host "You can manually validate with: winget validate --manifest `"$newVersionDir`"" -ForegroundColor Gray
        exit 1
    }

    # Publish manifest via Git CLI (supports GPG signing)
    Write-Host "`nPublishing manifest..." -ForegroundColor Cyan
    if (-not (Publish-ManifestViaGit -ForkRepo $forkRepo -ManifestPath $manifestPath -Version $Version -ManifestDir $newVersionDir -PackageId $PackageId -BranchName $branchName)) {
        throw "Failed to publish manifest"
    }

    # Create PR unless --NoPR
    if (-not $NoPR) {
        Write-Host "`nCreating pull request..." -ForegroundColor Cyan
        $forkOwner = $forkRepo.Split('/')[0]

        if (-not (New-PullRequest -ForkOwner $forkOwner -PackageId $PackageId -Version $Version -BranchName $branchName)) {
            throw "Failed to create pull request"
        }
    } else {
        Write-Host "`n✅ Manifest updated successfully (no PR created)" -ForegroundColor Green
    }

    # Cleanup temp directory
    Remove-Item $newVersionDir -Recurse -Force -ErrorAction SilentlyContinue

    Write-Host "`n✅ Update completed successfully!" -ForegroundColor Green
}
catch {
    Write-Error "`n❌ Error updating manifest: $_"
    Write-Error $_.ScriptStackTrace
    exit 1
}
