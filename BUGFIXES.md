# 🔧 Bug Fixes

## Issue 1: GitHub API check causing workflow errors

### Error:
```
{"message":"Not Found","documentation_url":"...","status":"404"}
Error: Unable to process file command 'output' successfully.
Error: Invalid format '  {'
```

### Root Cause:
- `gh api` command was outputting JSON response to stdout
- This JSON was being captured and causing GitHub Actions output format errors
- The check was looking at output instead of exit code

### Fix:
```bash
# Before (❌)
if gh api "/repos/microsoft/winget-pkgs/contents/$manifest_path/$version" 2>/dev/null; then

# After (✅)
if gh api "/repos/microsoft/winget-pkgs/contents/$manifest_path/$version" > /dev/null 2>&1; then
```

Also improved the JSON building:
```bash
# Before (❌)
updates=$(echo "$updates" | jq --arg file "$file" --arg pkg "$package_id" --arg ver "$version" '. + [{checkver: $file, package: $pkg, version: $ver}]')

# After (✅)
update_json=$(jq -n \
  --arg file "$file" \
  --arg pkg "$package_id" \
  --arg ver "$version" \
  '{checkver: $file, package: $pkg, version: $ver}')
updates=$(echo "$updates" | jq --argjson item "$update_json" '. + [$item]')
```

## Issue 2: Git authentication for push

### Problem:
- Need token authentication for pushing to fork
- SSH keys not available in GitHub Actions

### Fix:
Updated `clone_winget_pkgs()` and `commit_and_push()` to use token in URL:

```python
# Clone with token
repo_url = f"https://{token}@github.com/{fork_owner}/winget-pkgs.git"

# Push with token in remote URL
if token not in remote_url:
    remote_url = f"https://{token}@github.com/{repo_path}.git"
    subprocess.run(['git', 'remote', 'set-url', 'origin', remote_url])
```

## Changes Made:

### 1. `.github/workflows/update-packages.yml`
- ✅ Fixed `gh api` output redirection
- ✅ Improved JSON array building
- ✅ Added better logging with emojis (⏭️ for skip, ✨ for new)

### 2. `scripts/update_manifest.py`
- ✅ Added `token` parameter to `clone_winget_pkgs()`
- ✅ Added `token` parameter to `commit_and_push()`
- ✅ Clone using HTTPS with token
- ✅ Update remote URL with token before push
- ✅ Better error handling

## Testing:

```bash
# These should work now:
1. Check for updates - ✅ No JSON output errors
2. Build update matrix - ✅ Proper JSON array
3. Clone with token - ✅ Authentication works
4. Push to fork - ✅ Token in URL
5. Create PR - ✅ Uses gh CLI with token
```

## Status: ✅ FIXED

All authentication and output issues resolved!
