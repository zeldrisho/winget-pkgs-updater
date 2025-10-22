# Alacritty Manifest Update Analysis

## Issue Summary
When updating Alacritty from v0.16.0 to v0.16.1, the following properties need to be handled:

### Missing/Required Properties:
1. ✅ **ReleaseNotes** - Automatically fetched from GitHub API
2. ✅ **ReleaseNotesUrl** - Automatically fetched from GitHub API
3. ✅ **InstallationMetadata** - Static, copied from previous version
4. ✅ **AppsAndFeaturesEntries** - Partially automated (see details below)

---

## Solution Details

### 1. ReleaseNotes & ReleaseNotesUrl ✅ AUTOMATED
**Status:** Fully automated via checkver configuration

The checkver config already includes:
```yaml
updateMetadata:
  - ReleaseNotes
  - ReleaseNotesUrl
```

**How it works:**
- `check_version.py` fetches release info from GitHub API
- Release notes and URL are passed to `update_manifest.py`
- Manifest locale file is updated automatically

**Example for v0.16.1:**
```yaml
ReleaseNotes: |-
  ### Fixed
  - Crashes on GPUs with partial robustness support
ReleaseNotesUrl: https://github.com/alacritty/alacritty/releases/tag/v0.16.1
```

---

### 2. InstallationMetadata ✅ STATIC COPY
**Status:** Automatically copied from previous version

**Value (remains constant):**
```yaml
InstallationMetadata:
  DefaultInstallLocation: '%ProgramFiles%/Alacritty'
```

**How it works:**
- `update_manifest.py` copies the latest version folder
- All static properties (including InstallationMetadata) are preserved
- No manual intervention needed

---

### 3. AppsAndFeaturesEntries ⚠️ SEMI-AUTOMATED

#### ProductCode ✅ AUTOMATED
**Status:** Automatically extracted from MSI installer

The MSI ProductCode **changes with each version** and is automatically extracted:

**v0.16.0:**
```yaml
ProductCode: '{3A9A8C72-D108-4091-8E20-FD149C0DEBB8}'
```

**v0.16.1:**
```yaml
ProductCode: '{1AFCF3AD-0465-4039-B621-35B02E29CF6F}'
```

**How it works:**
1. `update_manifest.py` detects `.msi` installer URL
2. Downloads the MSI file to a temporary location
3. Runs `msiinfo export <file> Property` (from msitools package)
4. Extracts ProductCode from the Property table
5. Updates the manifest with the new ProductCode

**Requirements:**
- `msitools` package must be installed (✅ already available in dev container)
- MSI file must be accessible for download

#### UpgradeCode ✅ STATIC COPY
**Status:** Remains constant, copied from previous version

**Value (constant across all versions):**
```yaml
UpgradeCode: '{87C21C74-DBD5-4584-89D5-46D9CD0C40A7}'
```

**How it works:**
- UpgradeCode is a **static GUID** that identifies the product family
- It never changes across versions
- Automatically preserved when copying from previous version

---

## Update Workflow

When the GitHub Action runs for Alacritty v0.16.1:

### Step 1: Version Detection (`check_version.py`)
```bash
python3 scripts/check_version.py manifests/Alacritty.Alacritty.checkver.yaml
```

**Output:**
```json
{
  "version": "0.16.1",
  "installerUrl": "https://github.com/alacritty/alacritty/releases/download/v0.16.1/Alacritty-v0.16.1-installer.msi",
  "releaseNotes": "### Fixed\n- Crashes on GPUs with partial robustness support",
  "releaseNotesUrl": "https://github.com/alacritty/alacritty/releases/tag/v0.16.1"
}
```

### Step 2: Manifest Update (`update_manifest.py`)
```bash
python3 scripts/update_manifest.py <version_info.json>
```

**Actions performed:**
1. ✅ Clone microsoft/winget-pkgs repository
2. ✅ Find latest version (0.16.0)
3. ✅ Copy 0.16.0 folder → 0.16.1 folder
4. ✅ Download MSI installer
5. ✅ Calculate InstallerSha256
6. ✅ Extract ProductCode using msiinfo
7. ✅ Update all manifests:
   - `Alacritty.Alacritty.installer.yaml`:
     - PackageVersion: `0.16.0` → `0.16.1`
     - InstallerUrl: `v0.16.0` → `v0.16.1`
     - InstallerSha256: (new hash)
     - ReleaseDate: (today's date)
     - ProductCode: `{3A9A8C72...}` → `{1AFCF3AD...}` ✅
     - UpgradeCode: `{87C21C74...}` (unchanged) ✅
     - InstallationMetadata: (unchanged) ✅
   - `Alacritty.Alacritty.locale.en-US.yaml`:
     - PackageVersion: `0.16.0` → `0.16.1`
     - ReleaseNotes: (new content) ✅
     - ReleaseNotesUrl: (new URL) ✅
   - `Alacritty.Alacritty.yaml`:
     - PackageVersion: `0.16.0` → `0.16.1`

### Step 3: Pull Request Creation
The script creates a PR to microsoft/winget-pkgs with all changes.

---

## Verification

### Test the entire workflow:
```bash
# Check version detection
python3 scripts/check_version.py manifests/Alacritty.Alacritty.checkver.yaml

# Verify ProductCode extraction works
curl -sL "https://github.com/alacritty/alacritty/releases/download/v0.16.1/Alacritty-v0.16.1-installer.msi" \
  -o /tmp/test.msi
msiinfo export /tmp/test.msi Property | grep -E "^(ProductCode|UpgradeCode)"
```

**Expected output:**
```
ProductCode     {1AFCF3AD-0465-4039-B621-35B02E29CF6F}
UpgradeCode     {87C21C74-DBD5-4584-89D5-46D9CD0C40A7}
```

---

## Summary

### ✅ Fully Automated Properties:
- **ReleaseNotes** - Fetched from GitHub API
- **ReleaseNotesUrl** - Fetched from GitHub API
- **ProductCode** - Extracted from MSI using msitools
- **InstallerSha256** - Calculated from downloaded installer
- **ReleaseDate** - Set to current date

### ✅ Preserved Static Properties:
- **UpgradeCode** - Copied from previous version
- **InstallationMetadata** - Copied from previous version
- All other package metadata - Copied from previous version

### 🎯 Result:
**No manual intervention required!** The entire update process is fully automated for Alacritty.

---

## Technical Implementation Notes

### MSI ProductCode Extraction (in `update_manifest.py`):
```python
def extract_product_code_from_msi(msi_path: str) -> Optional[str]:
    """Extract ProductCode from MSI file using msitools"""
    result = subprocess.run(
        ['msiinfo', 'export', msi_path, 'Property'],
        capture_output=True,
        text=True,
        timeout=10
    )
    
    if result.returncode == 0 and result.stdout:
        for line in result.stdout.split('\n'):
            if line.startswith('ProductCode'):
                parts = line.split('\t')
                if len(parts) >= 2:
                    return parts[1].strip()
```

This function:
1. Uses `msiinfo` from msitools package
2. Exports the Property table from the MSI
3. Parses the tab-separated output
4. Returns the ProductCode GUID

### Dependencies:
- **msitools** - Available via `apt install msitools` (✅ pre-installed in dev container)
- **Python 3.11+** - For scripts
- **PowerShell 7.5+** - For custom version detection scripts (not used by Alacritty)

---

## Future Enhancements

### Potential improvements for other packages:
1. **UpgradeCode verification** - Could add a check to ensure UpgradeCode hasn't changed
2. **ProductCode validation** - Could verify the GUID format
3. **AppsAndFeaturesEntries position** - Ensure proper YAML formatting when adding new entries

These are not needed for Alacritty but could benefit other packages with more complex manifests.
