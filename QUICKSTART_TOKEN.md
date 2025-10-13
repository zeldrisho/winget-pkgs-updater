# 🎯 Quick Start - Fix Token Error

## ❌ Lỗi hiện tại:
```
Error: GITHUB_TOKEN or GH_TOKEN environment variable not set
```

## ✅ Cách fix nhanh (3 phút):

### Bước 1: Tạo Token (1 phút)
1. Vào: https://github.com/settings/tokens/new
2. Token name: `winget-pkgs-updater`
3. Expiration: **No expiration**
4. Check 2 boxes:
   - ☑️ `repo` (Full control)
   - ☑️ `workflow` (Update workflows)
5. Click **Generate token** ở cuối trang
6. **COPY TOKEN** (chuỗi bắt đầu bằng `ghp_...`)

### Bước 2: Add Secret (1 phút)
1. Vào: https://github.com/zeldrisho/winget-pkgs-updater/settings/secrets/actions/new
2. Name: `WINGET_PKGS_TOKEN` (phải đúng tên!)
3. Secret: Paste token vừa copy
4. Click **Add secret**

### Bước 3: Run lại Workflow (30 giây)
1. Vào: https://github.com/zeldrisho/winget-pkgs-updater/actions
2. Click **"Update WinGet Packages"**
3. Click **"Run workflow"** → **"Run workflow"**
4. Đợi workflow chạy → Check logs

---

## 📚 Chi tiết hơn?

- **Token setup:** [TOKEN_SETUP.md](TOKEN_SETUP.md)
- **Troubleshooting:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **Full checklist:** [SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)

---

## 🔍 Verify setup thành công:

### Workflow logs sẽ hiển thị:
```
✅ Updating VNGCorp.Zalo to version 25.10.2
✅ Cloning fork...
✅ Updating manifests...
✅ Creating PR...
✅ Successfully created PR for VNGCorp.Zalo version 25.10.2
```

### PR sẽ xuất hiện tại:
```
https://github.com/microsoft/winget-pkgs/pulls?q=author:zeldrisho
```

---

## ⚠️ Lưu ý quan trọng:

1. **Token name phải chính xác:** `WINGET_PKGS_TOKEN`
2. **Cần 2 permissions:** `repo` + `workflow`
3. **Fork microsoft/winget-pkgs** trước khi chạy:
   - https://github.com/microsoft/winget-pkgs → Click **Fork**
   - Hoặc workflow sẽ lỗi khi push

---

## 🚀 Sau khi setup:

- ✅ Workflow tự động chạy mỗi 6 giờ
- ✅ Detect version mới → Tự động tạo PR
- ✅ Microsoft reviewers sẽ thấy PR
- ✅ Merge → Version mới available trong WinGet

**Zero manual work!** 🎉
