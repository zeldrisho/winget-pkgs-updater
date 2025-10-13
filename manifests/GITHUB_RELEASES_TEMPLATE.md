# GitHub Releases Checkver Template

Template for packages that publish releases on GitHub.

## Basic Template

```yaml
packageIdentifier: Publisher.Package
manifestPath: manifests/p/Publisher/Package

checkver:
  type: script
  script: |
    # Get latest stable release from GitHub
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/owner/repo/releases/latest" -UserAgent "winget-pkgs-updater"
    if ($response.tag_name) {
      # Remove 'v' prefix if present
      $version = $response.tag_name -replace '^v', ''
      Write-Output $version
    }
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/Package_{version}_x64-setup.exe"
```

## How It Works

### 1. GitHub API Call
```powershell
Invoke-RestMethod -Uri "https://api.github.com/repos/owner/repo/releases/latest"
```
- Gets latest **stable** release (not pre-release)
- No authentication needed for public repos
- Returns JSON with release info

### 2. Version Extraction
```powershell
$version = $response.tag_name -replace '^v', ''
```
- Gets `tag_name` from release (e.g., "v2.4.4")
- Removes "v" prefix → "2.4.4"
- Outputs clean version number

### 3. Regex Validation
```yaml
regex: "([\\d\\.]+)"
```
- Validates version format (digits and dots only)
- Extracts first match if output has extra text

### 4. URL Construction
```yaml
installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/filename_{version}_x64.exe"
```
- `{version}` replaced with detected version
- Must match actual asset filename in release

## Real Examples

### Example 1: Seelen.SeelenUI

**Checkver:**
```yaml
packageIdentifier: Seelen.SeelenUI
manifestPath: manifests/s/Seelen/SeelenUI

checkver:
  type: script
  script: |
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/eythaann/Seelen-UI/releases/latest" -UserAgent "winget-pkgs-updater"
    if ($response.tag_name) {
      $version = $response.tag_name -replace '^v', ''
      Write-Output $version
    }
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://github.com/eythaann/Seelen-UI/releases/download/v{version}/Seelen.UI_{version}_x64-setup.exe"
```

**GitHub Release:**
- Tag: `v2.4.4`
- Asset: `Seelen.UI_2.4.4_x64-setup.exe`
- Detected version: `2.4.4`
- Constructed URL: `https://github.com/eythaann/Seelen-UI/releases/download/v2.4.4/Seelen.UI_2.4.4_x64-setup.exe`

### Example 2: Generic Pattern

**If your release has:**
- Tag: `v1.2.3`
- Asset: `MyApp-1.2.3-windows-x64.exe`

**Use this template:**
```yaml
installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/MyApp-{version}-windows-x64.exe"
```

## Finding Asset Filename

### Method 1: Check GitHub UI
1. Go to: `https://github.com/owner/repo/releases/latest`
2. Look at "Assets" section
3. Find Windows installer filename
4. Copy exact filename pattern

### Method 2: Use API
```bash
curl -s https://api.github.com/repos/owner/repo/releases/latest | jq -r '.assets[] | .name'
```

### Method 3: Download URL Pattern
If release has download link like:
```
https://github.com/owner/repo/releases/download/v1.2.3/app_1.2.3_setup.exe
```

Template is:
```yaml
installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app_{version}_setup.exe"
```

## Common Patterns

### Pattern 1: Version in Tag AND Filename
```yaml
# Tag: v1.2.3
# File: app_1.2.3_x64.exe
installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app_{version}_x64.exe"
```

### Pattern 2: Version Only in Tag
```yaml
# Tag: v1.2.3
# File: app-setup-x64.exe (no version in name)
installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app-setup-x64.exe"
```

### Pattern 3: Multiple Architectures
```yaml
# For x64:
installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app-{version}-x64.exe"

# For ARM64:
installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app-{version}-arm64.exe"
```

## Advanced: Pre-release vs Stable

### Get Latest Stable (Default)
```powershell
$response = Invoke-RestMethod -Uri "https://api.github.com/repos/owner/repo/releases/latest"
```
- Returns latest **stable** release only
- Ignores pre-releases
- ✅ Recommended for most packages

### Get Latest Including Pre-release
```powershell
$response = Invoke-RestMethod -Uri "https://api.github.com/repos/owner/repo/releases"
$version = $response[0].tag_name -replace '^v', ''
Write-Output $version
```
- Returns all releases (stable + pre-release)
- First item is latest (any type)
- ⚠️ May include beta/alpha versions

## Troubleshooting

### Issue: "Installer URL is not accessible"

**Possible causes:**
1. Filename pattern doesn't match actual asset name
2. Asset not uploaded yet for latest release
3. Release is draft (not public)

**Solution:**
```bash
# Check actual asset names
curl -s https://api.github.com/repos/owner/repo/releases/latest | jq -r '.assets[] | .name'

# Update installerUrlTemplate to match
```

### Issue: No version detected

**Possible causes:**
1. Repository has no releases
2. All releases are drafts
3. API rate limited

**Solution:**
```bash
# Check if releases exist
curl -s https://api.github.com/repos/owner/repo/releases/latest | jq .

# If empty: Repository has no stable releases
```

### Issue: Wrong version detected

**Possible causes:**
1. Regex pattern too broad
2. Script output has extra text

**Solution:**
```yaml
# Make regex more specific
regex: "^([\\d\\.]+)$"  # Exact match only

# Or clean output in script
$version = $version.Trim()
Write-Output $version
```

## Benefits

### ✅ For GitHub-based Projects
- Automatic version detection from releases
- No web scraping needed
- Official API (stable, fast)
- Works for any GitHub project with releases

### ✅ For Maintainers
- Simple setup (4 lines of script)
- Reliable (GitHub API SLA)
- No auth needed for public repos
- Easy to debug

## When to Use This Template

✅ **Use GitHub template when:**
- Package releases via GitHub Releases
- Releases have stable tags (v1.2.3)
- Installers uploaded as release assets

❌ **Don't use when:**
- Package has own website for downloads
- Releases on other platforms (GitLab, SourceForge, etc.)
- No GitHub releases (code-only repo)
- Custom version detection needed

## Alternative: GitHub API Advanced

For more control:

```yaml
checkver:
  type: script
  script: |
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/owner/repo/releases/latest"
    
    # Get version
    $version = $response.tag_name -replace '^v', ''
    
    # Find specific asset
    $asset = $response.assets | Where-Object { $_.name -like "*x64*.exe" }
    
    # Output version and actual download URL
    Write-Output "$version|$($asset.browser_download_url)"
  regex: "([\\d\\.]+)"
```

This gives you:
- Version number
- Actual download URL from API
- No need to guess filename

## Summary

**GitHub Releases Template:**
1. ✅ Gets latest stable release via API
2. ✅ Extracts version from tag name
3. ✅ Constructs download URL
4. ✅ Simple and reliable

**Perfect for open-source projects on GitHub!** 🚀
