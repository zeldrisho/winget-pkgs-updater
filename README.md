# WinGet Package Updater# WinGet Package Updater# WinGet Package Updater# winget-pkgs-updater



Automated tool to check for new package versions and create pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).



## FeaturesAutomated tool to check for new package versions and create pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).



- 🔄 **Automatic version detection** using PowerShell scripts or GitHub API

- 📦 **Manifest updates** - PackageVersion, InstallerUrl, InstallerSha256, SignatureSha256, ReleaseDate

- 🔍 **Smart PR management** - Skip if OPEN/MERGED, allow retry if CLOSED## FeaturesAutomated tool to check for new package versions and create pull requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs).Tự động tạo Pull Request lên [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) khi phát hiện phiên bản mới của các ứng dụng.

- ✅ **Universal version replacement** - Replaces version in all manifest fields automatically

- 🎯 **MSIX support** - Auto-calculates both InstallerSha256 and SignatureSha256

- 🤖 **GitHub Actions integration** - Runs on schedule or manually

- 🔄 **Automatic version detection** using PowerShell scripts or GitHub API

## Quick Start

- 📦 **Manifest updates** - PackageVersion, InstallerUrl, InstallerSha256, ReleaseDate

### 1. Fork Repository

Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) to your account.- 🔍 **Duplicate PR prevention** - Checks existing PRs before creating new ones## Features## 🚀 Quick Start (3 phút)



### 2. Setup Token- ✅ **Universal version replacement** - Replaces version in all manifest fields automatically

Create a GitHub Personal Access Token:

1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)- 🤖 **GitHub Actions integration** - Runs on schedule or manually

2. Click "Generate new token (classic)"

3. Select scopes: `repo` (all), `workflow`

4. Copy the token

## Quick Start- 🔄 **Automatic version detection** using PowerShell scripts or GitHub API### ❌ Gặp lỗi token?

### 3. Add Secret

In your repository settings:

1. Go to Settings → Secrets and variables → Actions

2. Click "New repository secret"### 1. Fork Repository- 📦 **Manifest updates** - PackageVersion, InstallerUrl, InstallerSha256, ReleaseDate👉 **[QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md)** - Fix trong 3 phút!

3. Name: `WINGET_PKGS_TOKEN`

4. Value: Your token from step 2Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) to your account.



### 4. Run Workflow- 🔍 **Duplicate PR prevention** - Checks existing PRs before creating new ones

Go to Actions → Update WinGet Packages → Run workflow

### 2. Setup Token

## Adding New Packages

Create a GitHub Personal Access Token with `repo` and `workflow` scopes:- ✅ **Universal version replacement** - Replaces version in all manifest fields automatically### ✅ Setup lần đầu?

### Method 1: Web Scraping

1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)

Example: VNGCorp.Zalo (HTTP redirect detection)

2. Click "Generate new token (classic)"- 🤖 **GitHub Actions integration** - Runs on schedule or manually1. **Fork repos:**

```yaml

packageIdentifier: VNGCorp.Zalo3. Select scopes: `repo` (all), `workflow`

manifestPath: manifests/v/VNGCorp/Zalo

4. Copy the token   - Fork repo này về account của bạn

checkver:

  type: script

  script: |

    $url = "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup.exe"### 3. Add Secret## Quick Start   - Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)

    $response = Invoke-WebRequest -Uri $url -MaximumRedirection 0 -ErrorAction SilentlyContinue

    if ($response.Headers.Location) {In your repository settings:

      $redirectUrl = $response.Headers.Location

      if ($redirectUrl -match "ZaloSetup-([\\d\\.]+)\\.exe") {1. Go to Settings → Secrets and variables → Actions

        Write-Output $matches[1]

      }2. Click "New repository secret"

    }

  regex: "([\\d\\.]+)"3. Name: `WINGET_PKGS_TOKEN`### 1. Fork Repository2. **Setup token:**



installerUrlTemplate: "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-{version}.exe"4. Value: Your token from step 2

```

Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) to your account.   - 📖 [QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md) - 3 phút

### Method 2: GitHub Releases

### 4. Run Workflow

Example: Seelen.SeelenUI (GitHub API + MSIX)

Go to Actions → Update WinGet Packages → Run workflow   - 📖 [TOKEN_SETUP.md](TOKEN_SETUP.md) - Chi tiết đầy đủ

```yaml

packageIdentifier: Seelen.SeelenUI

manifestPath: manifests/s/Seelen/SeelenUI

## Adding New Packages### 2. Setup Token

checkver:

  type: script

  script: |

    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/eythaann/Seelen-UI/releases/latest"### Method 1: Web Scraping (Example: VNGCorp.Zalo)Create a GitHub Personal Access Token with `repo` and `workflow` scopes:3. **Run workflow:**

    if ($response.tag_name) {

      $version = $response.tag_name -replace '^v', ''

      $version = $version + '.0'

      Write-Output $versionCreate `manifests/{Publisher}.{Package}.checkver.yaml`:1. Go to GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)   - Actions → Update WinGet Packages → Run workflow

    }

  regex: "([\\d\\.]+)"



installerUrlTemplate: "https://github.com/eythaann/Seelen-UI/releases/download/v{versionShort}/Seelen.SeelenUI_{version}_x64__p6yyn03m1894e.Msix"```yaml2. Click "Generate new token (classic)"

```

packageIdentifier: VNGCorp.Zalo

### Path Structure

# Path structure: manifests/{first-letter}/{publisher}/{package}3. Select scopes: `repo` (all), `workflow`4. **Đợi PR:**

**Important:** `manifestPath` must match the structure in microsoft/winget-pkgs:

# Example: https://github.com/microsoft/winget-pkgs/tree/master/manifests/v/VNGCorp/Zalo

```

manifests/{first-letter}/{publisher}/{package}manifestPath: manifests/v/VNGCorp/Zalo4. Copy the token   - Check tại: https://github.com/microsoft/winget-pkgs/pulls?q=author:YOUR_USERNAME

```



Examples:

- `Seelen` → `manifests/s/Seelen/SeelenUI`checkver:

- `VNGCorp` → `manifests/v/VNGCorp/Zalo`

- `Google` → `manifests/g/Google/Chrome`  type: script



**How to find:** Check [microsoft/winget-pkgs/tree/master/manifests](https://github.com/microsoft/winget-pkgs/tree/master/manifests)  script: |### 3. Add Secret---



## How It Works    $url = "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup.exe"



1. **Check Version** - Runs PowerShell script to detect latest version    $response = Invoke-WebRequest -Uri $url -MaximumRedirection 0 -ErrorAction SilentlyContinueIn your repository settings:

2. **Check Existing PR** - Searches for OPEN/MERGED PRs (skip if found)

3. **Download Installer** - Downloads installer file (if needed)    if ($response.Headers.Location) {

4. **Calculate Hashes** - InstallerSha256 + SignatureSha256 (for MSIX)

5. **Clone Fork** - Clones your winget-pkgs fork      $redirectUrl = $response.Headers.Location1. Go to Settings → Secrets and variables → Actions## 📚 Tài liệu

6. **Update Manifests** - Replaces all version occurrences + updates hashes

7. **Create PR** - Creates PR to microsoft/winget-pkgs      if ($redirectUrl -match "ZaloSetup-([\\d\\.]+)\\.exe") {



## PR Duplicate Prevention        Write-Output $matches[1]2. Click "New repository secret"



| PR State | Behavior |      }

|----------|----------|

| 🟢 OPEN | Skip - Already submitted |    }3. Name: `WINGET_PKGS_TOKEN`### 🔥 Nhanh

| 🟣 MERGED | Skip - Already in winget-pkgs |

| ⚪ CLOSED | Create new PR - Allow retry |  regex: "([\\d\\.]+)"



## Supported Formats4. Value: Your token from step 2- **[QUICKSTART_TOKEN.md](QUICKSTART_TOKEN.md)** - Fix token error trong 3 phút



| Format | Extension | InstallerSha256 | SignatureSha256 |installerUrlTemplate: "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-{version}.exe"

|--------|-----------|----------------|----------------|

| EXE | `.exe` | ✅ | - |```- **[SETUP_CHECKLIST.md](SETUP_CHECKLIST.md)** - Checklist đầy đủ

| MSIX | `.msix` | ✅ | ✅ |

| MSI | `.msi` | ✅ | - |



## Testing### Method 2: GitHub Releases (Example: Seelen.SeelenUI)### 4. Run Workflow



Test your checkver config locally:



```bashCreate `manifests/{Publisher}.{Package}.checkver.yaml`:Go to Actions → Update WinGet Packages → Run workflow### 📖 Chi tiết

python3 scripts/check_version.py manifests/YourPackage.checkver.yaml

```



## Troubleshooting```yaml- **[TOKEN_SETUP.md](TOKEN_SETUP.md)** - Hướng dẫn tạo Personal Access Token



### Error: GITHUB_TOKEN not setpackageIdentifier: Seelen.SeelenUI

Add `WINGET_PKGS_TOKEN` secret in repository settings.

# Path structure: manifests/{first-letter}/{publisher}/{package}## Adding New Packages- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Fix tất cả các lỗi thường gặp

### Error: Package not found

Check `manifestPath` is correct:# Example: https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/Seelen/SeelenUI

```

https://github.com/microsoft/winget-pkgs/tree/master/{manifestPath}manifestPath: manifests/s/Seelen/SeelenUI- **[TECHNICAL_DETAILS.md](TECHNICAL_DETAILS.md)** - Workflow run number vs ID

```



### PR already exists

Normal behavior - duplicate prevention is working. Check:checkver:### Method 1: Web Scraping (Example: VNGCorp.Zalo)

```

https://github.com/microsoft/winget-pkgs/pulls?q=is%3Apr+PackageIdentifier  type: script

```

  script: |### 🐛 Debug

## Documentation

    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/eythaann/Seelen-UI/releases/latest"

- [QUICKSTART.md](QUICKSTART.md) - 5-minute setup guide

- [CONTRIBUTING.md](CONTRIBUTING.md) - How to add packages    if ($response.tag_name) {Create `manifests/{Publisher}.{Package}.checkver.yaml`:- **[GITHUB_OUTPUT_FIX.md](GITHUB_OUTPUT_FIX.md)** - Fix multiline JSON output

- [manifests/README.md](manifests/README.md) - Checkver configuration guide

- [MSIX_SUPPORT.md](MSIX_SUPPORT.md) - MSIX package details      $version = $response.tag_name -replace '^v', ''



## License      Write-Output $version- **[BUGFIXES.md](BUGFIXES.md)** - Lịch sử các bugs đã fix



MIT    }


  regex: "([\\d\\.]+)"```yaml- **[CHANGELOG.md](CHANGELOG.md)** - Lịch sử thay đổi



installerUrlTemplate: "https://github.com/eythaann/Seelen-UI/releases/download/v{version}/Seelen.UI_{version}_x64-setup.exe"packageIdentifier: VNGCorp.Zalo

```

# Path structure: manifests/{first-letter}/{publisher}/{package}### 📝 Manifest

### Important Notes

# Example: https://github.com/microsoft/winget-pkgs/tree/master/manifests/v/VNGCorp/Zalo- **[manifests/README.md](manifests/README.md)** - Cấu trúc checkver config

1. **manifestPath structure**: `manifests/{first-letter}/{publisher}/{package}`

   - First letter is the lowercase first character of the publisher namemanifestPath: manifests/v/VNGCorp/Zalo- **[manifests/EXAMPLES.md](manifests/EXAMPLES.md)** - Ví dụ checkver configs

   - Example: `Seelen` → `manifests/s/Seelen/SeelenUI`

   - Example: `VNGCorp` → `manifests/v/VNGCorp/Zalo`



2. **Find existing manifests**: Check [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs/tree/master/manifests) for the exact path structurecheckver:---



3. **Version format**: Must match the version in microsoft/winget-pkgs (e.g., `2.3.12.0` not `2.3.12`)  type: script



## How It Works  script: |## ✨ Tính năng



1. **Check Version**: Runs PowerShell script to detect latest version    $url = "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup.exe"

2. **Compare with Existing PRs**: Checks if PR already exists (open/merged/closed)

3. **Download Installer**: Downloads the installer file    $response = Invoke-WebRequest -Uri $url -MaximumRedirection 0 -ErrorAction SilentlyContinue- ✅ Tự động detect version mới bằng PowerShell scripts

4. **Calculate SHA256**: Computes hash of the installer

5. **Update Manifest**: Replaces all version occurrences + updates SHA256 and ReleaseDate    if ($response.Headers.Location) {- ✅ Tự động tính SHA256 hash của installer

6. **Create PR**: If no duplicate found, creates PR to microsoft/winget-pkgs

      $redirectUrl = $response.Headers.Location- ✅ Clone manifest từ microsoft/winget-pkgs và update

## Troubleshooting

      if ($redirectUrl -match "ZaloSetup-([\\d\\.]+)\\.exe") {- ✅ Tự động tạo PR với format chuẩn

### Error: GITHUB_TOKEN not set

Add `WINGET_PKGS_TOKEN` secret in repository settings.        Write-Output $matches[1]- ✅ Chạy tự động mỗi 6 giờ



### Error: Package not found in microsoft/winget-pkgs      }- ✅ Support nhiều packages với checkver riêng

Check that the package exists and `manifestPath` is correct. Visit:

`https://github.com/microsoft/winget-pkgs/tree/master/{manifestPath}`    }- ✅ Full traceability: PR link về workflow run



### PR already exists  regex: "([\\d\\.]+)"

This is normal - the tool prevents duplicate PRs. Check existing PRs at:

`https://github.com/microsoft/winget-pkgs/pulls?q=is%3Apr+{PackageIdentifier}`---



## LicenseinstallerUrlTemplate: "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-{version}.exe"



MIT```## 🏗️ Architecture




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