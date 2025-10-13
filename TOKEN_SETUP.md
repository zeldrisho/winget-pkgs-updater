# 🔐 Token Setup Guide

## Problem

Workflow failing with:
```
Error: GITHUB_TOKEN or GH_TOKEN environment variable not set
```

## Why This Happens

The workflow needs a **Personal Access Token (PAT)** to:
1. Clone your fork of `microsoft/winget-pkgs`
2. Push commits to your fork
3. Create pull requests to `microsoft/winget-pkgs`

The built-in `GITHUB_TOKEN` **cannot** push to external repositories (forks).

## Solution: Create Personal Access Token

### Step 1: Generate Token

1. Go to: https://github.com/settings/tokens
2. Click **"Generate new token"** → **"Generate new token (classic)"**
3. Give it a name: `winget-pkgs-updater`
4. Set expiration: **No expiration** (or 1 year)
5. Select scopes:
   - ✅ **`repo`** (Full control of private repositories)
   - ✅ **`workflow`** (Update GitHub Action workflows)
6. Click **"Generate token"**
7. **COPY THE TOKEN** (you won't see it again!)

### Step 2: Add Secret to Repository

1. Go to your repo: https://github.com/zeldrisho/winget-pkgs-updater
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions**
4. Click **"New repository secret"**
5. Name: `WINGET_PKGS_TOKEN`
6. Value: Paste your token
7. Click **"Add secret"**

### Step 3: Verify Setup

Run workflow manually:
1. Go to **Actions** tab
2. Click **"Update WinGet Packages"**
3. Click **"Run workflow"**
4. Click **"Run workflow"** button

## Current Workflow Configuration

The workflow has **fallback support**:

```yaml
env:
  # Use WINGET_PKGS_TOKEN if available, fallback to GITHUB_TOKEN
  GITHUB_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN || github.token }}
  GH_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN || github.token }}
```

**Behavior:**
- ✅ If `WINGET_PKGS_TOKEN` exists → Use it (can push to fork)
- ⚠️  If not → Use `github.token` (limited, may fail on fork push)

## Token Permissions Required

Your PAT needs these permissions:

| Permission | Why |
|------------|-----|
| `repo` | Clone/push to your fork of winget-pkgs |
| `workflow` | Trigger and update workflows |
| `pull-requests` | Create PRs (included in `repo`) |

## Security Notes

- ✅ **Never** commit tokens to code
- ✅ **Always** use GitHub Secrets
- ✅ Token is encrypted and only available during workflow runs
- ✅ Token is hidden in logs (shows as `***`)

## Troubleshooting

### Error: "Resource not accessible by integration"
**Solution:** Token doesn't have `repo` or `workflow` scope. Regenerate with correct permissions.

### Error: "Bad credentials"
**Solution:** Token expired or invalid. Create new token and update secret.

### Error: "refusing to allow a Personal Access Token to create or update workflow"
**Solution:** Token needs `workflow` scope. Update token permissions.

## Quick Checklist

- [ ] Personal Access Token created
- [ ] Token has `repo` + `workflow` scopes
- [ ] Secret `WINGET_PKGS_TOKEN` added to repo
- [ ] Fork of `microsoft/winget-pkgs` created
- [ ] Workflow run triggered

---

**After setup, workflow will:**
1. ✅ Detect new versions
2. ✅ Clone your fork
3. ✅ Update manifests
4. ✅ Push to your fork
5. ✅ Create PR to microsoft/winget-pkgs

🎉 **Fully automated!**
