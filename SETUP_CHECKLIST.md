# ⚙️ Setup Checklist

## Các bước cần làm để chạy automation:

### ✅ 1. Fork microsoft/winget-pkgs
- [ ] Vào https://github.com/microsoft/winget-pkgs
- [ ] Click nút **Fork** ở góc trên bên phải
- [ ] Fork về account `zeldrisho`

### ✅ 2. Tạo Personal Access Token (PAT)
- [ ] Vào https://github.com/settings/tokens
- [ ] Click **Generate new token** → **Classic**
- [ ] Đặt tên: `winget-pkgs-updater`
- [ ] Chọn permissions:
  - [x] `repo` (Full control of private repositories)
  - [x] `workflow` (Update GitHub Action workflows)
- [ ] Click **Generate token**
- [ ] **Copy token** (chỉ hiện 1 lần!)

### ✅ 3. Add Secret vào repo này
- [ ] Vào https://github.com/zeldrisho/winget-pkgs-updater/settings/secrets/actions
- [ ] Click **New repository secret**
- [ ] Name: `WINGET_PKGS_TOKEN`
- [ ] Value: Paste token vừa copy
- [ ] Click **Add secret**

### ✅ 4. Verify setup
- [ ] Vào **Actions** tab trong repo này
- [ ] Click workflow **Update WinGet Packages**
- [ ] Click **Run workflow** → Chọn branch → **Run workflow**
- [ ] Xem log để check có lỗi gì không

### ✅ 5. Monitor kết quả
- [ ] Nếu có version mới, workflow sẽ tạo PR tự động
- [ ] Check PR tại: https://github.com/microsoft/winget-pkgs/pulls?q=is:pr+author:zeldrisho
- [ ] Đợi Microsoft review & merge

---

## 🧪 Test thủ công (Optional)

```bash
# 1. Check version
python scripts/check_version.py manifests/VNGCorp.Zalo.checkver.yaml

# 2. Test update (cần có fork & token)
# export GITHUB_TOKEN=your_token_here
# export GH_TOKEN=your_token_here
# python scripts/check_version.py manifests/VNGCorp.Zalo.checkver.yaml version.json
# python scripts/update_manifest.py version.json
```

---

## 📦 Thêm package mới

1. Tạo file checkver mới:
```bash
cp manifests/VNGCorp.Zalo.checkver.yaml manifests/NewPublisher.NewApp.checkver.yaml
```

2. Edit config:
- Đổi `packageIdentifier`
- Đổi `manifestPath` (path trong microsoft/winget-pkgs)
- Update `checkver` script/regex
- Update `installerUrlTemplate`

3. Test:
```bash
python scripts/check_version.py manifests/NewPublisher.NewApp.checkver.yaml
```

4. Commit & push → Workflow sẽ tự động pick up!

---

## ❓ Troubleshooting

**Lỗi "Permission denied"**
→ Check PAT token có đủ permissions không

**Lỗi "Repository not found"**
→ Đảm bảo đã fork microsoft/winget-pkgs

**Lỗi "PowerShell not found"**
→ Workflow tự install PowerShell, không cần lo

**PR không tạo được**
→ Check xem version đó có sẵn trong microsoft/winget-pkgs chưa

---

## 🎯 Status hiện tại

- [x] Code hoàn thiện
- [x] Workflow configured
- [x] Documentation ready
- [ ] **CẦN: Setup secrets**
- [ ] **CẦN: Fork microsoft/winget-pkgs**
- [ ] Ready to run!
