# 🔄 Migration Guide - Secret Name Change

## ⚠️ If you have old secrets, please update!

### What Changed?

**Old (Deprecated):**
- `WINGET_TOKEN` ❌
- `WINGET_FORK_REPO` ❌

**New (Current):**
- `WINGET_PKGS_TOKEN` ✅

### Why the Change?

1. **Simpler:** Only 1 secret needed instead of 2
2. **Auto-detection:** Fork URL is automatically detected from your GitHub username
3. **Consistent:** Matches workflow variable names
4. **Clear:** Name explicitly indicates it's for winget-pkgs operations

### How to Migrate (2 minutes)

#### Step 1: Create new secret
1. Go to: https://github.com/YOUR_USERNAME/winget-pkgs-updater/settings/secrets/actions
2. Click **"New repository secret"**
3. Name: `WINGET_PKGS_TOKEN`
4. Value: Same token you used for `WINGET_TOKEN` (or create new one)
5. Click **"Add secret"**

#### Step 2: Delete old secrets (Optional)
1. In the same page, find `WINGET_TOKEN`
2. Click **Remove** → Confirm
3. Find `WINGET_FORK_REPO`
4. Click **Remove** → Confirm

### If Your Token Expired

Create new token:
1. Go to: https://github.com/settings/tokens/new
2. Name: `winget-pkgs-updater`
3. Expiration: **No expiration**
4. Scopes:
   - ☑️ `repo` (Full control)
   - ☑️ `workflow` (Update workflows)
5. Click **"Generate token"**
6. **COPY TOKEN** (starts with `ghp_...`)
7. Add as secret `WINGET_PKGS_TOKEN`

### Verification

After migration, your secrets should look like:

```
✅ WINGET_PKGS_TOKEN (required)
❌ WINGET_TOKEN (can be deleted)
❌ WINGET_FORK_REPO (can be deleted)
```

### Test After Migration

1. Go to **Actions** tab
2. Click **"Update WinGet Packages"**
3. Click **"Run workflow"**
4. Check logs - should succeed without errors

### What About Fork URL?

**You don't need to specify it!**

The workflow automatically detects:
```yaml
fork_owner = os.getenv('GITHUB_REPOSITORY_OWNER', 'YOUR_USERNAME')
# Fork URL becomes: https://github.com/YOUR_USERNAME/winget-pkgs
```

If you fork microsoft/winget-pkgs to your account, it just works!

### FAQ

**Q: Can I keep using old secrets?**  
A: No, they are no longer read by the workflow. You must migrate to `WINGET_PKGS_TOKEN`.

**Q: What if I don't have old secrets?**  
A: Perfect! Just follow [TOKEN_SETUP.md](TOKEN_SETUP.md) to create `WINGET_PKGS_TOKEN`.

**Q: Do I need a new token?**  
A: No, you can reuse your existing token. Just rename the secret from `WINGET_TOKEN` to `WINGET_PKGS_TOKEN`.

**Q: Will workflow fail with old secrets?**  
A: Yes, you'll see: `Error: GITHUB_TOKEN or GH_TOKEN environment variable not set`

### Timeline

- **Before:** 2 secrets required (`WINGET_TOKEN` + `WINGET_FORK_REPO`)
- **Now:** 1 secret required (`WINGET_PKGS_TOKEN`)
- **Future:** Only `WINGET_PKGS_TOKEN` supported

### Need Help?

See:
- [QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md) - Quick setup
- [TOKEN_SETUP.md](TOKEN_SETUP.md) - Detailed guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common errors

---

**Migration takes 2 minutes. Do it now to avoid workflow failures! 🚀**
