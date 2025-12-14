# Test script for VC Redistributable version detection

$uri2 = "https://aka.ms/vc_redist.x64.exe"
$response = (Invoke-WebRequest $uri2).BaseResponse.RequestMessage.RequestUri.AbsolutePath

# For testing, we need to get the version from somewhere
# Let's also fetch the download page to get version info
$uri1 = "https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist"
$page = Invoke-WebRequest -Uri $uri1 -UseBasicParsing

# Extract version from the page
if ($page.Content -match 'Version.*?(\d+\.\d+\.\d+\.\d+)') {
    $version = $matches[1]
}

# Get display date
if ($page.Content -match 'ms\.date:\s*(\d{2}/\d{2}/\d{4})') {
    $displayDate = $matches[1]
}

Write-Host "=== Raw Values ===" -ForegroundColor Cyan
Write-Host "Version: $version"
Write-Host "Display Date: $displayDate"
Write-Host "Response Path: $response"
Write-Host ""

# Output in the format expected by regex
$output = "$version|$displayDate|$response"
Write-Host "=== Combined Output ===" -ForegroundColor Cyan
Write-Host $output
Write-Host ""

# Test regex extraction
$regex = "(?<version>[\d.]+)\|(?<displayDate>[^\|]+)\|/download/pr/(?<Uuid>[\w-]+)/(?<Hash>[\w]+)/"

Write-Host "=== Regex Test ===" -ForegroundColor Cyan
if ($output -match $regex) {
    Write-Host "Regex matched!" -ForegroundColor Green
    Write-Host "  version: $($matches['version'])"
    Write-Host "  displayDate: $($matches['displayDate'])"
    Write-Host "  Uuid: $($matches['Uuid'])"
    Write-Host "  Hash: $($matches['Hash'])"
    Write-Host ""
    
    # Build the installer URL
    $installerUrl = "https://download.visualstudio.microsoft.com/download/pr/$($matches['Uuid'])/$($matches['Hash'])/VC_redist.x64.exe"
    Write-Host "=== Generated Installer URL ===" -ForegroundColor Cyan
    Write-Host $installerUrl
} else {
    Write-Host "Regex did NOT match!" -ForegroundColor Red
    Write-Host "Check the pattern against the output above."
}
