# Manifest Update Behavior

## Automatic Updates

The following fields are automatically updated by the script:

### ✅ Always Updated

1. **PackageVersion** - Replaced everywhere
2. **InstallerUrl** - Version in URL replaced
3. **InstallerSha256** - Calculated from downloaded installer
4. **SignatureSha256** - Calculated for MSIX packages
5. **ReleaseDate** - Set to today's date (ISO 8601)
6. **InstallationMetadata.DefaultInstallLocation** - Version in path replaced
7. **Any field containing version** - Universal replacement

### 📋 Copied from Previous Version

These fields are copied from the latest existing version:

1. **ReleaseNotes** - Copied from previous version manifest
2. **ReleaseNotesUrl** - Copied from previous version manifest
3. **Other metadata** - Description, License, etc.

## Universal Version Replacement

The script uses a smart universal replacement strategy:

```python
# 1. Extract old version from PackageVersion field
old_version = "2.3.10.0"

# 2. Replace ALL occurrences
content = content.replace(old_version, new_version)
```

**This automatically updates:**
- `PackageVersion: 2.3.10.0` → `PackageVersion: 2.4.4.0`
- `InstallerUrl: .../v2.3.10/...` → `InstallerUrl: .../v2.4.4/...`
- `DefaultInstallLocation: ..._2.3.10.0_...` → `DefaultInstallLocation: ..._2.4.4.0_...`
- Any other field with version

## Example: Seelen.SeelenUI Update

### Before (2.3.10.0)

```yaml
# Seelen.SeelenUI.installer.yaml
PackageVersion: 2.3.10.0
InstallerUrl: https://github.com/eythaann/Seelen-UI/releases/download/v2.3.10/Seelen.SeelenUI_2.3.10.0_x64__p6yyn03m1894e.Msix
InstallerSha256: 70941F9F4C55ADB62D29EB2DEFD1732A1FFA6C00A7F03425646707F6E7E39563
SignatureSha256: 1EE5F22F79B0BB774C732166EFC90830A645A9648A00633B5DDA65E016F55E9D
InstallationMetadata:
  DefaultInstallLocation: '%ProgramFiles%\WindowsApps\Seelen.SeelenUI_2.3.10.0_x64__p6yyn03m1894e'
ReleaseDate: 2025-07-10

# Seelen.SeelenUI.locale.en-US.yaml
PackageVersion: 2.3.10.0
ReleaseNotes: |-
  hotfix
  - missing react icons.
  Full Changelog: v2.3.9...v2.3.10
```

### After (2.4.4.0) - Automatic Update

```yaml
# Seelen.SeelenUI.installer.yaml
PackageVersion: 2.4.4.0                    # ← Updated by universal replacement
InstallerUrl: https://github.com/eythaann/Seelen-UI/releases/download/v2.4.4/Seelen.SeelenUI_2.4.4.0_x64__p6yyn03m1894e.Msix  # ← Updated by universal replacement
InstallerSha256: 6C9F22AEAC3CBB5AD6803538534C029C8D244F181EACAFC859F1ED1610EE70FF  # ← Calculated
SignatureSha256: 6F43A2F1650DBF7EB63E22F923D473FCD961E01ACBC851FD6B81FC4D523FFF53  # ← Calculated
InstallationMetadata:
  DefaultInstallLocation: '%ProgramFiles%\WindowsApps\Seelen.SeelenUI_2.4.4.0_x64__p6yyn03m1894e'  # ← Updated by universal replacement
ReleaseDate: 2025-10-13                    # ← Set to today

# Seelen.SeelenUI.locale.en-US.yaml
PackageVersion: 2.4.4.0                    # ← Updated by universal replacement
ReleaseNotes: |-                           # ← Copied from old version (needs manual update if desired)
  hotfix
  - missing react icons.
  Full Changelog: v2.3.9...v2.3.10
```

## Updating ReleaseNotes

### Option 1: Accept Old Release Notes
The PR will work fine with old release notes. It's just documentation.

### Option 2: Manual Update
After PR is created, edit the manifest files to update ReleaseNotes.

### Option 3: Add GitHub Integration (Future)
Could fetch release notes from GitHub API during manifest update.

## Why This Approach?

**Pros:**
- ✅ Simple and reliable
- ✅ Universal - works for any package structure
- ✅ No package-specific code needed
- ✅ Automatically handles version in URLs, paths, etc.

**Cons:**
- ⚠️ ReleaseNotes may be outdated (acceptable for most cases)

## Testing

Test with:
```bash
# Run test workflow (no PR creation)
Actions → Test Manifest Checker → Run workflow

# Test locally
python3 scripts/check_version.py manifests/Seelen.SeelenUI.checkver.yaml
```

## Summary

| Field | Update Method | Source |
|-------|--------------|--------|
| PackageVersion | Universal replacement | Checkver script |
| InstallerUrl | Universal replacement | Checkver template |
| InstallerSha256 | Calculated | Downloaded installer |
| SignatureSha256 | Calculated | MSIX signature |
| ReleaseDate | Set to today | System date |
| InstallationMetadata | Universal replacement | Old manifest |
| ReleaseNotes | Copied | Old manifest ⚠️ |
| Other fields | Copied | Old manifest |

**Note:** The ⚠️ on ReleaseNotes means it may be outdated. This is acceptable for automation. Manual update available if needed.
