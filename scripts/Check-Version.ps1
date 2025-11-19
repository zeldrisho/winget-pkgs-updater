#Requires -Version 7.4

<#
.SYNOPSIS
    Check for package version updates

.DESCRIPTION
    Detects new versions by checking GitHub releases or running PowerShell scripts

.PARAMETER CheckverPath
    Path to the checkver configuration file

.PARAMETER OutputFile
    Optional path to save version info JSON

.EXAMPLE
    ./Check-Version.ps1 manifests/Microsoft.PowerShell.checkver.yaml
    ./Check-Version.ps1 manifests/Package.checkver.yaml version_info.json
#>

param(
    [Parameter(Mandatory, Position=0)]
    [string]$CheckverPath,

    [Parameter(Position=1)]
    [string]$OutputFile
)

$ErrorActionPreference = 'Stop'

# Import module
Import-Module "$PSScriptRoot/WinGetUpdater.psm1" -Force

try {
    $result = Test-PackageUpdate -CheckverPath $CheckverPath -OutputFile $OutputFile

    if ($result) {
        # Success - new version found
        exit 0
    } else {
        # No update found
        Write-Host "No update found or error occurred" -ForegroundColor Yellow
        exit 1
    }
}
catch {
    Write-Error "Error: $_"
    Write-Error $_.ScriptStackTrace
    exit 1
}
