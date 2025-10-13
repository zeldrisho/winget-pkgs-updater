# 🔧 GitHub Output Format Fix

## Problem

GitHub Actions was failing with:
```
Error: Unable to process file command 'output' successfully.
Error: Invalid format '  {'
```

## Root Cause

**Multiline JSON** in `$GITHUB_OUTPUT` needs special handling!

### ❌ Wrong Way (Before)
```bash
echo "matrix=$updates" >> $GITHUB_OUTPUT
```

When `$updates` contains:
```json
[
  {
    "package": "VNGCorp.Zalo"
  }
]
```

GitHub Actions sees:
```
matrix=[
  {
```
And fails because the value spans multiple lines!

## Solution

Use **EOF delimiter** for multiline output:

### ✅ Correct Way (After)
```bash
echo "matrix<<EOF" >> $GITHUB_OUTPUT
echo "$updates" >> $GITHUB_OUTPUT
echo "EOF" >> $GITHUB_OUTPUT
```

This creates:
```
matrix<<EOF
[
  {
    "package": "VNGCorp.Zalo"
  }
]
EOF
```

GitHub Actions correctly parses everything between `matrix<<EOF` and `EOF` as the value!

## Changes Made

### File: `.github/workflows/update-packages.yml`

**Before:**
```yaml
echo "matrix=$updates" >> $GITHUB_OUTPUT
```

**After:**
```yaml
# Use EOF delimiter for multiline JSON output
echo "matrix<<EOF" >> $GITHUB_OUTPUT
echo "$updates" >> $GITHUB_OUTPUT
echo "EOF" >> $GITHUB_OUTPUT
```

**Also removed unnecessary `set-matrix` step:**
- Job output now comes directly from `steps.check-updates.outputs.matrix`
- Simplified workflow by removing redundant step

## Reference

Official GitHub Docs: [Multiline Strings](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#multiline-strings)

## Testing

Verified with local simulation:
```bash
✅ Valid JSON parsing
✅ Correct matrix building
✅ Workflow logic works end-to-end
```

---

**Status:** ✅ Fixed and tested - ready for production!
