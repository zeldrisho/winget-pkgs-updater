# WinGet Package Updater# winget-pkgs-updater



Automated tool to check for new package versions and create pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).Tự động tạo Pull Request lên [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) khi phát hiện phiên bản mới của các ứng dụng.



## Features## 🚀 Quick Start (3 phút)



- 🔄 **Automatic version detection** using PowerShell scripts or GitHub API### ❌ Gặp lỗi token?

- 📦 **Manifest updates** - PackageVersion, InstallerUrl, InstallerSha256, ReleaseDate👉 **[QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md)** - Fix trong 3 phút!

- 🔍 **Duplicate PR prevention** - Checks existing PRs before creating new ones

- ✅ **Universal version replacement** - Replaces version in all manifest fields automatically### ✅ Setup lần đầu?

- 🤖 **GitHub Actions integration** - Runs on schedule or manually1. **Fork repos:**

   - Fork repo này về account của bạn

## Quick Start   - Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)



### 1. Fork Repository2. **Setup token:**

Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) to your account.   - 📖 [QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md) - 3 phút

   - 📖 [TOKEN_SETUP.md](TOKEN_SETUP.md) - Chi tiết đầy đủ

### 2. Setup Token

Create a GitHub Personal Access Token with `repo` and `workflow` scopes:3. **Run workflow:**

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)   - Actions → Update WinGet Packages → Run workflow

2. Click "Generate new token (classic)"

3. Select scopes: `repo` (all), `workflow`4. **Đợi PR:**

4. Copy the token   - Check tại: https://github.com/microsoft/winget-pkgs/pulls?q=author:YOUR_USERNAME



### 3. Add Secret---

In your repository settings:

1. Go to Settings → Secrets and variables → Actions## 📚 Tài liệu

2. Click "New repository secret"

3. Name: `WINGET_PKGS_TOKEN`### 🔥 Nhanh

4. Value: Your token from step 2- **[QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md)** - Fix token error trong 3 phút

- **[SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)** - Checklist đầy đủ

### 4. Run Workflow

Go to Actions → Update WinGet Packages → Run workflow### 📖 Chi tiết

- **[TOKEN_SETUP.md](TOKEN_SETUP.md)** - Hướng dẫn tạo Personal Access Token

## Adding New Packages- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Fix tất cả các lỗi thường gặp

- **[TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md)** - Workflow run number vs ID

### Method 1: Web Scraping (Example: VNGCorp.Zalo)

### 🐛 Debug

Create `manifests/{Publisher}.{Package}.checkver.yaml`:- **[GITHUB_OUTPUT_FIX.md](GITHUB_OUTPUT_FIX.md)** - Fix multiline JSON output

- **[BUGFIXES.md](BUGFIXES.md)** - Lịch sử các bugs đã fix

```yaml- **[CHANGELOG.md](CHANGELOG.md)** - Lịch sử thay đổi

packageIdentifier: VNGCorp.Zalo

# Path structure: manifests/{first-letter}/{publisher}/{package}### 📝 Manifest

# Example: https://github.com/microsoft/winget-pkgs/tree/master/manifests/v/VNGCorp/Zalo- **[manifests/README.md](manifests/README.md)** - Cấu trúc checkver config

manifestPath: manifests/v/VNGCorp/Zalo- **[manifests/EXAMPLES.md](manifests/EXAMPLES.md)** - Ví dụ checkver configs



checkver:---

  type: script

  script: |## ✨ Tính năng

    $url = "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup.exe"

    $response = Invoke-WebRequest -Uri $url -MaximumRedirection 0 -ErrorAction SilentlyContinue- ✅ Tự động detect version mới bằng PowerShell scripts

    if ($response.Headers.Location) {- ✅ Tự động tính SHA256 hash của installer

      $redirectUrl = $response.Headers.Location- ✅ Clone manifest từ microsoft/winget-pkgs và update

      if ($redirectUrl -match "ZaloSetup-([\\d\\.]+)\\.exe") {- ✅ Tự động tạo PR với format chuẩn

        Write-Output $matches[1]- ✅ Chạy tự động mỗi 6 giờ

      }- ✅ Support nhiều packages với checkver riêng

    }- ✅ Full traceability: PR link về workflow run

  regex: "([\\d\\.]+)"

---

installerUrlTemplate: "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-{version}.exe"

```## 🏗️ Architecture



### Method 2: GitHub Releases (Example: Seelen.SeelenUI)### Workflow

```

Create `manifests/{Publisher}.{Package}.checkver.yaml`:1. GitHub Actions runs every 6 hours (or manual)

2. Scan manifests/*.checkver.yaml files

```yaml3. Run PowerShell scripts to detect versions

packageIdentifier: Seelen.SeelenUI4. Compare with microsoft/winget-pkgs

# Path structure: manifests/{first-letter}/{publisher}/{package}5. If new version found:

# Example: https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/Seelen/SeelenUI   ├─ Clone your fork

manifestPath: manifests/s/Seelen/SeelenUI   ├─ Copy latest manifest

   ├─ Update version & SHA256

checkver:   ├─ Commit & push to fork

  type: script   └─ Create PR to microsoft/winget-pkgs

  script: |```

    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/eythaann/Seelen-UI/releases/latest"

    if ($response.tag_name) {### Files Structure

      $version = $response.tag_name -replace '^v', ''```

      Write-Output $versionwinget-pkgs-updater/

    }├── .github/workflows/

  regex: "([\\d\\.]+)"│   └── update-packages.yml      # Main workflow

├── manifests/

installerUrlTemplate: "https://github.com/eythaann/Seelen-UI/releases/download/v{version}/Seelen.UI_{version}_x64-setup.exe"│   ├── VNGCorp.Zalo.checkver.yaml  # Checkver config

```│   └── ...more packages...

├── scripts/

### Important Notes│   ├── check_version.py         # Version detection

│   └── update_manifest.py       # Manifest update & PR creation

1. **manifestPath structure**: `manifests/{first-letter}/{publisher}/{package}`└── docs/

   - First letter is the lowercase first character of the publisher name    ├── QUICKSTART_TOKEN.md      # 3-min setup

   - Example: `Seelen` → `manifests/s/Seelen/SeelenUI`    ├── TOKEN_SETUP.md           # Detailed token guide

   - Example: `VNGCorp` → `manifests/v/VNGCorp/Zalo`    ├── TROUBLESHOOTING.md       # All errors & fixes

    └── ...more docs...

2. **Find existing manifests**: Check [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs/tree/master/manifests) for the exact path structure```



3. **Version format**: Must match the version in microsoft/winget-pkgs (e.g., `2.3.12.0` not `2.3.12`)### Checkver Config Format

```yaml

## How It WorkspackageIdentifier: VNGCorp.Zalo

manifestPath: manifests/v/VNGCorp/Zalo

1. **Check Version**: Runs PowerShell script to detect latest versioncheckver:

2. **Download Installer**: Downloads the installer file  type: script

3. **Calculate SHA256**: Computes hash of the installer  script: |

4. **Update Manifest**: Replaces all version occurrences + updates SHA256 and ReleaseDate    # PowerShell script to get download URL

5. **Check Existing PR**: Searches for open/merged PRs with same version    # Can use Invoke-WebRequest, API calls, etc.

6. **Create PR**: If no duplicate found, creates PR to microsoft/winget-pkgs  regex: "ZaloSetup-([\\d\\.]+)\\.exe"

installerUrlTemplate: "https://example.com/ZaloSetup-{version}.exe"

## Troubleshooting```



### Error: GITHUB_TOKEN not set---

Add `WINGET_PKGS_TOKEN` secret in repository settings.

## 🔧 Adding New Packages

### Error: Package not found in microsoft/winget-pkgs

Check that the package exists and `manifestPath` is correct. Visit:### 1. Create checkver config

`https://github.com/microsoft/winget-pkgs/tree/master/{manifestPath}`

File: `manifests/Your.Package.checkver.yaml`

### PR already exists```yaml

This is normal - the tool prevents duplicate PRs. Check existing PRs at:packageIdentifier: Your.Package

`https://github.com/microsoft/winget-pkgs/pulls?q=is%3Apr+{PackageIdentifier}`manifestPath: manifests/y/Your/Package

checkver:

## License  type: script

  script: |

MIT    # PowerShell to get version

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