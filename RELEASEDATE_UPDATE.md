# 📅 ReleaseDate Auto-Update

## What It Does

The workflow automatically updates the `ReleaseDate` field in manifest files to the current date when a new version is detected.

## Format

- **Standard**: ISO 8601 date format (`YYYY-MM-DD`)
- **Example**: `2025-10-13`
- **Field**: `ReleaseDate` in installer manifest

## How It Works

### In Code

**File**: `scripts/update_manifest.py`

```python
from datetime import datetime

# Get today's date in ISO format
today = datetime.now().strftime('%Y-%m-%d')

# Update ReleaseDate in manifest
content = re.sub(
    r'ReleaseDate:\s*[\d-]+',
    f'ReleaseDate: {today}',
    content
)
```

### Process Flow

```
1. New version detected (e.g., 25.10.2)
2. Clone manifest from microsoft/winget-pkgs
3. Update fields:
   ├─ PackageVersion: 25.10.2
   ├─ InstallerUrl: ...ZaloSetup-25.10.2.exe
   ├─ InstallerSha256: [calculated hash]
   └─ ReleaseDate: 2025-10-13 ✨ AUTO
4. Commit and create PR
```

## Example

### Before (Old Manifest)

```yaml
PackageIdentifier: VNGCorp.Zalo
PackageVersion: 25.8.3
InstallerUrl: https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-25.8.3.exe
InstallerSha256: ABC123...
ReleaseDate: 2024-08-01
```

### After (Updated by Workflow)

```yaml
PackageIdentifier: VNGCorp.Zalo
PackageVersion: 25.10.2
InstallerUrl: https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-25.10.2.exe
InstallerSha256: DEF456...
ReleaseDate: 2025-10-13
```

## Why This Matters

### For WinGet Users
- ✅ Accurate release date information
- ✅ Better version tracking
- ✅ Proper sorting in package managers

### For Microsoft Reviewers
- ✅ No manual date entry needed
- ✅ Consistent date format
- ✅ Reflects actual PR creation date

### For Package Maintainers
- ✅ Zero manual work
- ✅ No date mistakes
- ✅ Always current

## Fields Updated

| Field | Description | Example |
|-------|-------------|---------|
| `PackageVersion` | Version number | `25.10.2` |
| `InstallerUrl` | Download URL with version | `...ZaloSetup-25.10.2.exe` |
| `InstallerSha256` | SHA256 hash (calculated) | `ABC123...` |
| `ReleaseDate` | Release date (today) ✨ | `2025-10-13` |

## Timezone

- Uses **system timezone** (GitHub Actions runs in UTC)
- Date format: `YYYY-MM-DD` (no timezone info needed)
- Always current day when workflow runs

## Testing

### Test Locally

```python
from datetime import datetime

today = datetime.now().strftime('%Y-%m-%d')
print(f"Today's date: {today}")
# Output: Today's date: 2025-10-13
```

### Verify in PR

Check the manifest diff in your PR:

```diff
- ReleaseDate: 2024-08-01
+ ReleaseDate: 2025-10-13
```

## Manual Override (Not Recommended)

If you need to set a specific date (rare cases):

1. **After workflow creates PR**
2. **Manually edit the manifest in your fork**
3. **Push update** (will update existing PR)

But normally, auto-date is what you want! ✅

## Configuration

**No configuration needed!** 

The date is automatically set when:
- New version is detected
- Manifest is updated
- PR is created

## Related Files

- `scripts/update_manifest.py` - Contains date update logic
- `.github/workflows/update-packages.yml` - Runs the workflow
- Manifest files in `microsoft/winget-pkgs` - Gets updated

## FAQ

**Q: What if I run workflow multiple times same day?**  
A: Date stays the same (same day), only matters for first PR creation.

**Q: What timezone is used?**  
A: UTC (GitHub Actions default), but date is date, no timezone in format.

**Q: Can I use a different date format?**  
A: No, WinGet requires ISO 8601 (`YYYY-MM-DD`).

**Q: What if my local date is different?**  
A: Workflow runs on GitHub servers (UTC), uses their date.

---

**Summary**: ReleaseDate automatically set to today when new version is detected. Zero configuration, zero manual work! 🎉
