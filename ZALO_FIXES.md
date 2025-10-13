# Zalo Manifest Fixes - Summary

## Issues Fixed

### 1. Incorrect Manifest Structure ❌ → ✅

**Before:** Single monolithic YAML file with wrong format
```
manifests/
└── VNGCorp.Zalo.yaml  (incorrect format)
```

**After:** Simplified checkver configuration only
```
manifests/
└── VNGCorp.Zalo.checkver.yaml  # Only version checking config
```

**Why this approach?**
- ✅ No need to maintain manifest copies in this repo
- ✅ GitHub Actions fetches latest manifests from microsoft/winget-pkgs
- ✅ Always up-to-date with upstream
- ✅ Minimal storage and maintenance

**Workflow:**
1. Checkver config defines how to detect new versions
2. GitHub Actions runs periodically
3. When new version found:
   - Clone fork of microsoft/winget-pkgs
   - Fetch latest manifest
   - Update version + calculate SHA256
   - Create PR with format: `New version: VNGCorp.Zalo version 25.8.3`

### 2. Incorrect Checkver Method ❌ → ✅

**Before:** Simple web scraping that didn't work
- Tried to parse download page HTML
- Couldn't handle redirects
- Didn't follow the actual download flow

**After:** PowerShell script-based checkver (following Microsoft's approach)
```yaml
checkver:
  type: script
  script: |
    try {
      $response = Invoke-WebRequest -Uri "https://zalo.me/download/zalo-pc" 
        -MaximumRedirection 0 
        -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0" 
        -ErrorAction SilentlyContinue
      if ($response.Headers.Location) {
        Write-Output $response.Headers.Location.OriginalString
      }
    } catch {
      if ($_.Exception.Response.Headers.Location) {
        Write-Output $_.Exception.Response.Headers.Location.OriginalString
      }
    }
  regex: ZaloSetup-([\d\.]+)\.exe
```

This method:
- ✅ Follows HTTP redirects to get actual download URL
- ✅ Extracts version from the redirect location
- ✅ Matches Microsoft's winget-pkgs approach for Zalo

### 3. Updated check_version.py Script

Added support for PowerShell script-based version checking:
- Executes PowerShell scripts via `pwsh` command
- Applies regex patterns to script output
- Falls back to web scraping if script method not available
- Compatible with both simple and complex checkver configurations

## Testing Results

```bash
$ python scripts/check_version.py manifests/VNGCorp/Zalo/checkver.yaml

Checking for updates: VNGCorp.Zalo
Script output: https://res-download-pc.zadn.vn/win/ZaloSetup-25.10.2.exe
Extracted version: 25.10.2
Latest version found: 25.10.2
Installer URL: https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-25.10.2.exe

✅ Successfully detected version 25.10.2
```

## References

- Official Zalo manifests: https://github.com/microsoft/winget-pkgs/tree/master/manifests/v/VNGCorp/Zalo
- Example version 25.8.3: https://github.com/microsoft/winget-pkgs/tree/master/manifests/v/VNGCorp/Zalo/25.8.3
- WinGet Manifest Schema 1.10.0: https://aka.ms/winget-manifest.version.1.10.0.schema.json

## Dependencies Installed

- PowerShell 7.5.3 (`pwsh`) - Required for script-based checkver execution
