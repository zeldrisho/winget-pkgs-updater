# MSIX Support Summary

## ✅ Added SignatureSha256 Calculation

### Problem
Seelen.SeelenUI uses MSIX installer format which requires **two** hash fields:
1. `InstallerSha256` - Hash of the MSIX file itself
2. `SignatureSha256` - Hash of the digital signature inside the MSIX

**Before:** Only calculated InstallerSha256 ❌  
**After:** Calculates both hashes automatically ✅

### Solution

Added PowerShell-based signature extraction:

```python
def calculate_msix_signature_sha256(msix_path: str) -> Optional[str]:
    """
    Calculate SHA256 of MSIX signature using PowerShell.
    Two methods:
    1. Get-AuthenticodeSignature (preferred)
    2. Extract AppxSignature.p7x from MSIX zip (fallback)
    """
```

### How It Works

1. **Detect MSIX file** by extension (`.msix`)
2. **Download installer** to temporary file
3. **Calculate InstallerSha256** (file hash)
4. **Extract signature** using PowerShell:
   - Try `Get-AuthenticodeSignature` first
   - Fallback to extracting `AppxSignature.p7x` from MSIX
5. **Calculate SignatureSha256** (signature hash)
6. **Update manifests** with both hashes

### Example Output

```
Downloading: https://github.com/eythaann/Seelen-UI/releases/download/v2.4.4/Seelen.SeelenUI_2.4.4.0_x64__p6yyn03m1894e.Msix
✅ Downloaded
Calculated InstallerSha256: 6C9F22AEAC3CBB5AD6803538534C029C8D244F181EACAFC859F1ED1610EE70FF
MSIX package detected, calculating SignatureSha256...
Calculated SignatureSha256: 6F43A2F1650DBF7EB63E22F923D473FCD961E01ACBC851FD6B81FC4D523FFF53
✅ Updated InstallerSha256
✅ Updated SignatureSha256
```

## 📦 Updated Manifest Fields

The script now updates all these fields automatically:

### Seelen.SeelenUI.installer.yaml
```yaml
PackageVersion: 2.4.4.0                    # ← Updated
InstallerUrl: .../v2.4.4/Seelen.SeelenUI_2.4.4.0_...  # ← Updated
InstallerSha256: 6C9F22AEAC3CBB5A...       # ← Updated ✅
SignatureSha256: 6F43A2F1650DBF7E...       # ← Updated ✅ NEW!
ReleaseDate: 2025-10-13                    # ← Updated
```

### Seelen.SeelenUI.locale.en-US.yaml
```yaml
PackageVersion: 2.4.4.0                    # ← Updated
ReleaseNotes: |-                           # ← Updated from GitHub
  features
  - add emergency shortcut...
  enhancements
  - improve development ecosystem...
  fix
  - not considering multiple batteries...
```

## 🔧 Technical Details

### PowerShell Script
```powershell
$packagePath = "path/to/file.msix"

# Method 1: Get certificate hash
$signHash = (Get-AuthenticodeSignature $packagePath).SignerCertificate.GetCertHashString("SHA256")

# Method 2: Extract signature file from MSIX
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($packagePath)
$sigFile = $zip.Entries | Where-Object { $_.FullName -eq "AppxSignature.p7x" }
$sigHash = (Get-FileHash -Path $extractedSig -Algorithm SHA256).Hash
```

### File Type Detection
```python
# Auto-detect MSIX by file extension
file_ext = '.msix' if installer_url.lower().endswith('.msix') else '.exe'
is_msix = file_ext == '.msix'

if is_msix:
    signature_sha256 = calculate_msix_signature_sha256(tmp_path)
```

## ✅ Checkver Config (Already Correct)

The Seelen.SeelenUI checkver config was already correct:

```yaml
packageIdentifier: Seelen.SeelenUI
manifestPath: manifests/s/Seelen/SeelenUI

checkver:
  type: script
  script: |
    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/eythaann/Seelen-UI/releases/latest"
    if ($response.tag_name) {
      $version = $response.tag_name -replace '^v', ''
      $version = $version + '.0'      # v2.4.4 → 2.4.4.0
      Write-Output $version
    }

# Uses {versionShort} for download (v2.4.4) and {version} for filename (2.4.4.0)
installerUrlTemplate: "https://github.com/eythaann/Seelen-UI/releases/download/v{versionShort}/Seelen.SeelenUI_{version}_x64__p6yyn03m1894e.Msix"
```

**Version Handling:**
- GitHub release: `v2.4.4` (tag)
- WinGet manifest: `2.4.4.0` (PackageVersion)
- Download URL: `v2.4.4` (path) + `2.4.4.0` (filename)

## 🎯 Supported Package Types

| Type | Extension | InstallerSha256 | SignatureSha256 | Example |
|------|-----------|----------------|----------------|---------|
| EXE | `.exe` | ✅ | ❌ | VNGCorp.Zalo |
| MSIX | `.msix` | ✅ | ✅ | Seelen.SeelenUI |
| MSI | `.msi` | ✅ | ❌ | (future) |

## 🚀 Commits to Push

```bash
git push origin main  # Push 3 commits
```

**Commit History:**
```
9d0b5d3 - feat: Add SignatureSha256 calculation for MSIX packages ⭐ NEW!
c4d8925 - docs: Add final update summary
f35ebc7 - fix: Remove Vietnamese text and optimize PR duplicate check
```

## 📊 Complete Flow

```
1. GitHub Actions triggers workflow
2. check_version.py detects new version (2.4.4 → 2.4.4.0)
3. update_manifest.py:
   a. Check if PR exists → No
   b. Download MSIX file
   c. Calculate InstallerSha256 ✅
   d. Detect MSIX format
   e. Calculate SignatureSha256 ✅ NEW!
   f. Clone fork
   g. Update all manifest files
   h. Commit and push
   i. Create PR
4. PR created with all hashes updated ✅
```

## ✨ Benefits

- **Automatic**: No manual hash calculation needed
- **Reliable**: Uses PowerShell's built-in cryptography
- **Fallback**: Two methods to extract signature
- **Universal**: Works for any MSIX package
- **Safe**: Validates signatures during extraction

---

**Ready to deploy!** All MSIX packages will now be handled correctly with both hash fields updated automatically. 🎉
