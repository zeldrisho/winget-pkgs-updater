# ReleaseNotes Auto-Fetch - Complete! ✅

## Problem Solved

**Before:** ReleaseNotes copied from old version (outdated)  
**After:** ReleaseNotes fetched fresh from GitHub API for each release ✅

## How It Works

### 1. Version Detection (check_version.py)

```python
# Detect GitHub API URL from checkver script
github_api_match = re.search(r'github\.com/repos/([^/]+)/([^/]+)/releases', script)

# Fetch release by tag
# Example: 2.4.4.0 → v2.4.4 (removes .0 suffix, adds v prefix)
api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag_name}"

# Get release notes and URL
release_notes = release_data.get('body')
release_notes_url = release_data.get('html_url')
```

### 2. Manifest Update (update_manifest.py)

```python
# Update locale files with release notes
if is_locale_file and release_notes:
    updated_content = update_manifest_content(
        content, version, sha256, signature_sha256,
        release_notes, release_notes_url  # ← New!
    )
```

### 3. YAML Format

Uses block scalar format (`|-`) for multi-line notes:

```yaml
ReleaseNotes: |-
  ### features
  
  - add emergency shortcut to stop seelen process (Ctrl + Win + Alt + K).
  
  ### enhancements
  
  - improve development ecosystem of resources via embedding of yaml files.
  - allow open dev tools on release builds.
  
  ### fix
  
  - not considering multiple batteries on setups.
  - app not forcing restart on pc sleep/resume.
ReleaseNotesUrl: https://github.com/eythaann/Seelen-UI/releases/tag/v2.4.4
```

## Version Handling

Handles both formats automatically:

| GitHub Tag | WinGet Version | Download URL | Works? |
|------------|----------------|--------------|--------|
| `v2.4.4` | `2.4.4.0` | `.../v2.4.4/...2.4.4.0...` | ✅ |
| `v2.3.12` | `2.3.12.0` | `.../v2.3.12/...2.3.12.0...` | ✅ |

**Logic:**
- Script adds `.0` suffix: `v2.4.4` → `2.4.4.0`
- Download uses `{versionShort}`: removes `.0` → `v2.4.4`
- Release notes fetch: removes `.0`, adds `v` → `v2.4.4`

## Example Output

```bash
Checking for updates: Seelen.SeelenUI
✅ Latest version found: 2.4.4.0
Fetching release info from: https://api.github.com/repos/eythaann/Seelen-UI/releases/tags/v2.4.4
✅ Fetched release notes (1230 chars)
📝 Release notes available (1230 chars)

Updating manifests...
  Updated: Seelen.SeelenUI.installer.yaml
  Updated: Seelen.SeelenUI.locale.en-US.yaml
    ✅ Updated ReleaseNotes (block scalar)
    ✅ Updated ReleaseNotesUrl
  Updated: Seelen.SeelenUI.yaml
```

## What Gets Updated

| File | Field | Source | Example |
|------|-------|--------|---------|
| installer.yaml | PackageVersion | Checkver | `2.4.4.0` |
| installer.yaml | InstallerUrl | Template | `.../v2.4.4/...2.4.4.0...` |
| installer.yaml | InstallerSha256 | Calculated | `6C9F22AE...` |
| installer.yaml | SignatureSha256 | Calculated | `6F43A2F1...` |
| installer.yaml | InstallationMetadata | Universal replacement | `..._2.4.4.0_...` |
| installer.yaml | ReleaseDate | Today | `2025-10-13` |
| locale.yaml | PackageVersion | Universal replacement | `2.4.4.0` |
| **locale.yaml** | **ReleaseNotes** | **GitHub API** ⭐ | **Fresh from v2.4.4** |
| **locale.yaml** | **ReleaseNotesUrl** | **GitHub API** ⭐ | **Release URL** |
| version.yaml | PackageVersion | Universal replacement | `2.4.4.0` |

## Supported Packages

| Package | Method | ReleaseNotes |
|---------|--------|--------------|
| VNGCorp.Zalo | Web scraping | ❌ (no GitHub) |
| Seelen.SeelenUI | GitHub releases | ✅ Auto-fetch |
| Any GitHub package | GitHub API | ✅ Auto-fetch |

**Note:** Only works for packages using GitHub Releases API in checkver script.

## Testing

### Test Locally
```bash
# Check version detection and release notes fetch
python3 scripts/check_version.py manifests/Seelen.SeelenUI.checkver.yaml

# Look for:
# ✅ Fetched release notes (XXXX chars)
# "releaseNotes": "..."
# "releaseNotesUrl": "..."
```

### Test Workflow
```bash
# Run test workflow (no PR)
Actions → Test Manifest Checker → Run workflow → Seelen.SeelenUI

# Run full workflow (with PR)
Actions → Update WinGet Packages → Run workflow
```

## Benefits

✅ **Always fresh** - Release notes match the version  
✅ **Automatic** - No manual editing needed  
✅ **Accurate** - Direct from publisher  
✅ **Multi-line support** - Handles formatting  
✅ **URL included** - Links to full release page  

## Technical Details

### Regex Pattern
```python
# Extract GitHub repo from checkver script
github_api_match = re.search(
    r'github\.com/repos/([^/]+)/([^/]+)/releases', 
    script
)
owner = github_api_match.group(1)  # eythaann
repo = github_api_match.group(2)   # Seelen-UI
```

### Tag Conversion
```python
# WinGet version to GitHub tag
version = "2.4.4.0"
tag_version = re.sub(r'\.0$', '', version)  # 2.4.4
tag_name = f"v{tag_version}"                 # v2.4.4
```

### YAML Formatting
```python
# Format for YAML block scalar
yaml_notes = release_notes.replace('\r\n', '\n').replace('\r', '\n')
formatted = f'ReleaseNotes: |-\n  {yaml_notes.replace("\n", "\n  ")}\n'
```

## Commits

```bash
git push origin main  # Push 4 commits
```

**Commits:**
1. `99bfeb8` - feat: Auto-fetch ReleaseNotes from GitHub API ⭐
2. `9711f81` - docs: Add update complete summary
3. `8032f18` - docs: Add manifest update behavior documentation
4. `02cbf89` - refactor: Clean README, add test workflow

---

## Summary

**Problem:** "phải update, ko copy từ version trc" ✅  
**Solution:** Auto-fetch from GitHub API ✅  
**Format:** YAML block scalar (|-) ✅  
**Works for:** All GitHub-based packages ✅  

**Ready to deploy!** 🚀
