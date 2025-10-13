# Setup Summary - WinGet Package Updater

## ✅ Đã hoàn thành

### 1. Cấu trúc repo tối giản
```
manifests/
└── VNGCorp.Zalo.checkver.yaml  # Chỉ config checkver

scripts/
├── check_version.py            # Check version mới
└── update_manifest.py          # Update manifest & tạo PR
```

### 2. Workflow tự động
- **Check versions**: Tìm tất cả `.checkver.yaml` files
- **Detect updates**: Chạy PowerShell script để detect version
- **Create PR**: Tự động fork, clone, update, push & create PR

### 3. Quy trình hoạt động

```
1. GitHub Actions chạy theo lịch (6h/lần)
2. Đọc file VNGCorp.Zalo.checkver.yaml
3. Chạy PowerShell script → detect version 25.10.2
4. Clone fork của microsoft/winget-pkgs
5. Tìm manifest latest version (VD: 25.8.3)
6. Copy → Update → Tính SHA256
7. Commit & Push lên fork
8. Tạo PR với format:
   Title: "New version: VNGCorp.Zalo version 25.10.2"
   Body: "Automated by zeldrisho/winget-pkgs-updater in workflow run #123"
```

### 4. Cần setup

**Trong GitHub repo settings:**
1. Tạo Personal Access Token (classic) với permissions:
   - `repo` (full control)
   - `workflow`
2. Thêm secret: `WINGET_PKGS_TOKEN` = token vừa tạo
3. Fork repository `microsoft/winget-pkgs` về account của bạn

### 5. Thêm package mới

Chỉ cần tạo file mới trong `manifests/`:

```yaml
# manifests/Publisher.Package.checkver.yaml
packageIdentifier: Publisher.Package
manifestPath: manifests/p/Publisher/Package

checkver:
  type: script  # hoặc 'web' cho simple scraping
  script: |
    # PowerShell code
  regex: Package-([\d\.]+)\.exe

installerUrlTemplate: https://example.com/Package-{version}.exe
```

### 6. Test local

```bash
# Test checkver
python scripts/check_version.py manifests/VNGCorp.Zalo.checkver.yaml

# Sẽ output:
# - Version detected: 25.10.2
# - Installer URL
# - SHA256 (nếu download)
```

## ✅ Lợi ích

- **Minimal storage**: Chỉ lưu checkver config, không lưu manifest
- **Always updated**: Fetch manifest mới nhất từ microsoft/winget-pkgs
- **Auto SHA256**: Tự động download & tính hash
- **Clean PRs**: Format đúng chuẩn Microsoft
- **Scalable**: Dễ thêm package mới

## 📝 Cần làm tiếp

1. ✅ Fork `microsoft/winget-pkgs`
2. ✅ Tạo Personal Access Token
3. ✅ Add secret `WINGET_PKGS_TOKEN`
4. ✅ Test workflow bằng cách push code
5. ⏳ Monitor PR trong microsoft/winget-pkgs

## 🎯 Kết quả

Khi có version mới:
- ✅ Tự động detect (PowerShell script)
- ✅ Tự động tính SHA256
- ✅ Tự động tạo PR format chuẩn
- ✅ Không cần maintain manifest trong repo này

---

**Status**: ✅ **SẴN SÀNG** - Chỉ cần setup secrets và có thể chạy!
