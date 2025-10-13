# 🔍 Troubleshooting Common Errors

## Error: "GITHUB_TOKEN or GH_TOKEN environment variable not set"

### Cause
Secret `WINGET_PKGS_TOKEN` không tồn tại hoặc chưa được cấu hình.

### Solution
1. ✅ Tạo Personal Access Token: [TOKEN_SETUP.md](TOKEN_SETUP.md)
2. ✅ Add secret với tên **chính xác**: `WINGET_PKGS_TOKEN`
3. ✅ Verify secret đã được add: Settings → Secrets → Actions

### How to Verify
```bash
# In workflow, secret should be available as:
${{ secrets.WINGET_PKGS_TOKEN }}
```

---

## Error: "Invalid format '  {'"

### Cause
Multiline JSON không được format đúng trong `$GITHUB_OUTPUT`.

### Solution
✅ **Fixed in commit 70e4d98** - Dùng EOF delimiter:
```yaml
echo "matrix<<EOF" >> $GITHUB_OUTPUT
echo "$updates" >> $GITHUB_OUTPUT
echo "EOF" >> $GITHUB_OUTPUT
```

### Verify
Pull latest code:
```bash
git pull origin main
```

---

## Error: "Resource not accessible by integration"

### Cause
Token không có đủ permissions.

### Solution
Token cần có scopes:
- ✅ `repo` (Full control)
- ✅ `workflow` (Update workflows)

### How to Fix
1. Vào: https://github.com/settings/tokens
2. Click vào token `winget-pkgs-updater`
3. Check permissions:
   - Must have ✅ `repo`
   - Must have ✅ `workflow`
4. If missing → Regenerate token with correct scopes
5. Update secret `WINGET_PKGS_TOKEN` với token mới

---

## Error: "refusing to allow a Personal Access Token to create or update workflow"

### Cause
Token thiếu `workflow` permission.

### Solution
1. Regenerate token với **`workflow`** scope
2. Update secret `WINGET_PKGS_TOKEN`

---

## Error: "Bad credentials"

### Cause
- Token đã expire
- Token bị revoke
- Token sai

### Solution
1. Tạo token mới: https://github.com/settings/tokens
2. Copy token mới
3. Update secret: Settings → Secrets → Actions → Edit `WINGET_PKGS_TOKEN`

---

## Error: "remote: Permission to microsoft/winget-pkgs.git denied"

### Cause
Đang push trực tiếp vào `microsoft/winget-pkgs` thay vì fork.

### Solution
1. ✅ Fork repo `microsoft/winget-pkgs` về account của bạn
2. ✅ Script sẽ tự động push vào fork: `zeldrisho/winget-pkgs`
3. ✅ Từ fork sẽ tạo PR về upstream

### Verify
Check fork exists:
```bash
# Should exist:
https://github.com/zeldrisho/winget-pkgs
```

---

## Error: "Version 25.10.2 already exists"

### Cause
Version đã có trong `microsoft/winget-pkgs` repository.

### Solution
✅ **This is normal!** Workflow sẽ:
1. Check version existence
2. Skip nếu đã tồn tại
3. Chỉ tạo PR cho version mới

### Expected Output
```
⏭️  Version 25.10.2 already exists in microsoft/winget-pkgs, skipping
```

---

## Workflow không chạy tự động

### Cause
Schedule chưa trigger lần đầu.

### Solution
**Chạy thủ công lần đầu:**
1. Go to **Actions** tab
2. Click **Update WinGet Packages**
3. Click **Run workflow**
4. Select branch: `main`
5. Click **Run workflow** button

**Schedule sẽ chạy sau đó:**
- Cron: `0 */6 * * *` (every 6 hours)
- Next runs: 00:00, 06:00, 12:00, 18:00 UTC

---

## Workflow pass nhưng không có PR

### Possible Causes

**1. No new version found**
```
Latest version found: 25.10.2
⏭️  Version 25.10.2 already exists, skipping
```
✅ This is normal - no action needed.

**2. Fork chưa tồn tại**
- Must fork: https://github.com/microsoft/winget-pkgs
- Fork to: https://github.com/zeldrisho/winget-pkgs

**3. Token không có quyền tạo PR**
- Check token có `repo` scope
- Check token chưa expire

### How to Debug
Check workflow logs:
1. Go to Actions tab
2. Click vào workflow run
3. Click vào job `Update ...`
4. Read logs để xem lỗi gì

---

## JSON parsing errors

### Error Examples
```
parse error: Invalid numeric literal at line 1, column 5
```

### Cause
- checkver output không phải valid URL/version
- PowerShell script lỗi
- Website thay đổi format

### Solution
Test checkver locally:
```bash
python scripts/check_version.py manifests/VNGCorp.Zalo.checkver.yaml
```

Check output:
- ✅ Should be URL: `https://...ZaloSetup-25.10.2.exe`
- ❌ If error/HTML → Fix PowerShell script in checkver.yaml

---

## Quick Debug Commands

### Test version check locally
```bash
cd /workspaces/winget-pkgs-updater
python scripts/check_version.py manifests/VNGCorp.Zalo.checkver.yaml
```

### Test with output file
```bash
python scripts/check_version.py manifests/VNGCorp.Zalo.checkver.yaml version.json
cat version.json | jq .
```

### Test manifest update (needs token)
```bash
export GITHUB_TOKEN=your_token_here
export GH_TOKEN=your_token_here
export GITHUB_REPOSITORY_OWNER=zeldrisho
export GITHUB_RUN_NUMBER=1
export GITHUB_RUN_ID=12345

python scripts/update_manifest.py version.json
```

### Check workflow syntax
```bash
# GitHub Actions extension can validate
# Or use: https://rhysd.github.io/actionlint/
```

---

## Still Having Issues?

### Checklist
- [ ] Fork of `microsoft/winget-pkgs` exists
- [ ] Personal Access Token created with `repo` + `workflow`
- [ ] Secret `WINGET_PKGS_TOKEN` added to repo
- [ ] Latest code pulled (`git pull`)
- [ ] Workflow run manually at least once

### Get Help
1. Check workflow logs in Actions tab
2. Review error message
3. Find matching section in this document
4. Follow solution steps

### Common Mistakes
- ❌ Forgot to fork `microsoft/winget-pkgs`
- ❌ Token name typo: `WINGET_PKG_TOKEN` instead of `WINGET_PKGS_TOKEN`
- ❌ Token thiếu `repo` hoặc `workflow` scope
- ❌ Chưa pull latest code (still has old bugs)

---

**Most issues = Missing token or fork!** 🔑
