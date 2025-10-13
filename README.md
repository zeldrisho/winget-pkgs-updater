# winget-pkgs-updater

Tự động tạo Pull Request lên [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) khi phát hiện phiên bản mới của các ứng dụng.

## 🚀 Quick Start (3 phút)

### ❌ Gặp lỗi token?
👉 **[QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md)** - Fix trong 3 phút!

### ✅ Setup lần đầu?
1. **Fork repos:**
   - Fork repo này về account của bạn
   - Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)

2. **Setup token:**
   - 📖 [QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md) - 3 phút
   - 📖 [TOKEN_SETUP.md](TOKEN_SETUP.md) - Chi tiết đầy đủ

3. **Run workflow:**
   - Actions → Update WinGet Packages → Run workflow

4. **Đợi PR:**
   - Check tại: https://github.com/microsoft/winget-pkgs/pulls?q=author:YOUR_USERNAME

---

## 📚 Tài liệu

### 🔥 Nhanh
- **[QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md)** - Fix token error trong 3 phút
- **[SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)** - Checklist đầy đủ

### 📖 Chi tiết
- **[TOKEN_SETUP.md](TOKEN_SETUP.md)** - Hướng dẫn tạo Personal Access Token
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Fix tất cả các lỗi thường gặp
- **[TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md)** - Workflow run number vs ID

### 🐛 Debug
- **[GITHUB_OUTPUT_FIX.md](GITHUB_OUTPUT_FIX.md)** - Fix multiline JSON output
- **[BUGFIXES.md](BUGFIXES.md)** - Lịch sử các bugs đã fix
- **[CHANGELOG.md](CHANGELOG.md)** - Lịch sử thay đổi

### 📝 Manifest
- **[manifests/README.md](manifests/README.md)** - Cấu trúc checkver config
- **[manifests/EXAMPLES.md](manifests/EXAMPLES.md)** - Ví dụ checkver configs

---

## ✨ Tính năng

- ✅ Tự động detect version mới bằng PowerShell scripts
- ✅ Tự động tính SHA256 hash của installer
- ✅ Clone manifest từ microsoft/winget-pkgs và update
- ✅ Tự động tạo PR với format chuẩn
- ✅ Chạy tự động mỗi 6 giờ
- ✅ Support nhiều packages với checkver riêng
- ✅ Full traceability: PR link về workflow run

---

## 🏗️ Architecture

### Workflow
```
1. GitHub Actions runs every 6 hours (or manual)
2. Scan manifests/*.checkver.yaml files
3. Run PowerShell scripts to detect versions
4. Compare with microsoft/winget-pkgs
5. If new version found:
   ├─ Clone your fork
   ├─ Copy latest manifest
   ├─ Update version & SHA256
   ├─ Commit & push to fork
   └─ Create PR to microsoft/winget-pkgs
```

### Files Structure
```
winget-pkgs-updater/
├── .github/workflows/
│   └── update-packages.yml      # Main workflow
├── manifests/
│   ├── VNGCorp.Zalo.checkver.yaml  # Checkver config
│   └── ...more packages...
├── scripts/
│   ├── check_version.py         # Version detection
│   └── update_manifest.py       # Manifest update & PR creation
└── docs/
    ├── QUICKSTART_TOKEN.md      # 3-min setup
    ├── TOKEN_SETUP.md           # Detailed token guide
    ├── TROUBLESHOOTING.md       # All errors & fixes
    └── ...more docs...
```

### Checkver Config Format
```yaml
packageIdentifier: VNGCorp.Zalo
manifestPath: manifests/v/VNGCorp/Zalo
checkver:
  type: script
  script: |
    # PowerShell script to get download URL
    # Can use Invoke-WebRequest, API calls, etc.
  regex: "ZaloSetup-([\\d\\.]+)\\.exe"
installerUrlTemplate: "https://example.com/ZaloSetup-{version}.exe"
```

---

## 🔧 Adding New Packages

### 1. Create checkver config

File: `manifests/Your.Package.checkver.yaml`
```yaml
packageIdentifier: Your.Package
manifestPath: manifests/y/Your/Package
checkver:
  type: script
  script: |
    # PowerShell to get version
    Invoke-WebRequest -Uri "https://api.example.com/version"
  regex: "v([\\d\\.]+)"
installerUrlTemplate: "https://example.com/installer-{version}.exe"
```

### 2. Test locally
```bash
python scripts/check_version.py manifests/Your.Package.checkver.yaml
```

### 3. Commit and push
```bash
git add manifests/Your.Package.checkver.yaml
git commit -m "feat: Add Your.Package checkver config"
git push
```

### 4. Workflow will auto-detect on next run!

---

## 🐛 Common Issues

### "Error: GITHUB_TOKEN not set"
👉 See [QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md)

### "Invalid format" error
👉 Fixed in latest version, pull updates

### Workflow passes but no PR
- Check if version already exists in microsoft/winget-pkgs
- Verify fork exists: `https://github.com/YOUR_USERNAME/winget-pkgs`
- Check workflow logs for errors

### Need more help?
📖 [TROUBLESHOOTING.md](TROUBLESHOOTING.md) covers all errors!

---

## 📊 Status & Progress

### Current Status
✅ **Production Ready!**

### What's Working
- ✅ PowerShell-based version detection
- ✅ Multiline JSON output (EOF delimiter)
- ✅ SHA256 hash calculation
- ✅ Automatic PR creation
- ✅ Run number display (#42 format)
- ✅ Full documentation

### Known Limitations
- ⚠️ Requires Personal Access Token (github.token has limited permissions)
- ⚠️ Must fork microsoft/winget-pkgs first
- ⚠️ PowerShell scripts are package-specific

### Roadmap
- [ ] Add more package checkver configs
- [ ] Web UI for monitoring
- [ ] Email notifications
- [ ] Batch PR support

---

## 📄 License

MIT License - See [LICENSE](LICENSE)

---

## 🙏 Credits

- [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) - The official WinGet repository
- Inspired by update automation tools from various package managers

---

## 💬 Support

- 📖 **Documentation:** Check files in this repo
- 🐛 **Issues:** GitHub Issues tab
- 💡 **Questions:** GitHub Discussions

---

**Made with ❤️ for automated package management**

### Thủ công

1. Vào tab "Actions" trong repository
2. Chọn workflow "Update WinGet Packages"
3. Click "Run workflow"
4. Chọn package cần kiểm tra (hoặc để trống để kiểm tra tất cả)

## Cấu trúc thư mục

```
.
├── .github/
│   └── workflows/
│       └── update-packages.yml    # GitHub Actions workflow
├── manifests/                     # Cấu hình các packages
│   ├── README.md                  # Tài liệu manifest
│   ├── EXAMPLES.md                # Ví dụ cấu hình
│   └── VNGCorp.Zalo.yaml         # Package đầu tiên
├── scripts/                       # Scripts Python
│   ├── check_version.py           # Kiểm tra version mới
│   ├── generate_manifest.py       # Tạo manifest files
│   ├── add_package.py             # Helper thêm package
│   ├── test_manifest.py           # Test manifest generation
│   └── requirements.txt           # Python dependencies
├── SETUP.md                       # Hướng dẫn cài đặt chi tiết
├── CONTRIBUTING.md                # Hướng dẫn đóng góp
└── README.md                      # File này
```

## Công nghệ sử dụng

- **Python 3.11+**: Scripts xử lý version và manifest
- **GitHub Actions**: Automation và scheduling
- **YAML**: Configuration format
- **WinGet Manifest Schema 1.6.0**: Format manifest chuẩn

## Tham khảo

Dự án được lấy cảm hứng từ:

- [SpecterShell/Dumplings](https://github.com/SpecterShell/Dumplings)
- [vedantmgoyal9/winget-pkgs-automation](https://github.com/vedantmgoyal9/winget-pkgs-automation)
- [ScoopInstaller/GithubActions](https://github.com/ScoopInstaller/GithubActions)

## License

GPL-3.0 License - Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

## Đóng góp

Contributions are welcome! Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết cách thêm packages mới.

## Hỗ trợ

Nếu gặp vấn đề:
1. Kiểm tra [SETUP.md](SETUP.md) và [CONTRIBUTING.md](CONTRIBUTING.md)
2. Xem workflow logs trong tab Actions
3. Mở issue với thông tin chi tiết