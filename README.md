# winget-pkgs-updater

Tự động tạo Pull Request lên [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) khi phát hiện phiên bản mới của các ứng dụng.

## 🚀 Bắt đầu nhanh

**Xem [QUICKSTART.md](QUICKSTART.md)** - Hướng dẫn cài đặt trong 5 phút!

## Tính năng

- ✅ Tự động kiểm tra phiên bản mới của các ứng dụng
- ✅ Tạo manifest theo đúng format của microsoft/winget-pkgs
- ✅ Tự động tạo Pull Request sử dụng tài khoản GitHub của bạn
- ✅ Hỗ trợ nhiều ứng dụng với cấu hình độc lập
- ✅ Chạy định kỳ bằng GitHub Actions

## Bắt đầu nhanh

👉 **[QUICKSTART.md](QUICKSTART.md)** - Hướng dẫn cài đặt trong 5 phút!

### 1. Fork repository này

### 2. Fork microsoft/winget-pkgs về tài khoản của bạn

### 3. Tạo Personal Access Token với quyền `repo` và `workflow`

### 4. Thêm secrets vào repository:
- `WINGET_TOKEN`: Personal Access Token của bạn
- `WINGET_FORK_REPO`: Tên fork của bạn (ví dụ: `username/winget-pkgs`)

### 5. Kích hoạt GitHub Actions

Xem hướng dẫn chi tiết trong [SETUP.md](SETUP.md).

## Tài liệu

- **[QUICKSTART.md](QUICKSTART.md)** - 🚀 Hướng dẫn cài đặt nhanh 5 phút
- **[SETUP.md](SETUP.md)** - Hướng dẫn cài đặt chi tiết
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Hướng dẫn thêm packages mới
- **[manifests/README.md](manifests/README.md)** - Cấu trúc manifest
- **[manifests/EXAMPLES.md](manifests/EXAMPLES.md)** - Ví dụ cấu hình

## Cài đặt

### 1. Fork repository này

Fork repository về tài khoản GitHub của bạn.

### 2. Fork microsoft/winget-pkgs

Fork [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) về tài khoản của bạn. Đây là nơi các Pull Request sẽ được tạo trước khi submit lên repo chính.

### 3. Tạo Personal Access Token (PAT)

1. Truy cập [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Tạo token mới với các quyền:
   - `repo` (Full control of private repositories)
   - `workflow` (Update GitHub Action workflows)
3. Copy token và lưu lại

### 4. Cấu hình Secrets

Trong repository của bạn, thêm các secrets sau (Settings > Secrets and variables > Actions):

- `WINGET_TOKEN`: Personal Access Token vừa tạo
- `WINGET_FORK_REPO`: Tên fork của bạn (ví dụ: `username/winget-pkgs`)

## Cấu hình ứng dụng

### Thêm ứng dụng mới

#### Cách 1: Sử dụng helper script (Khuyến nghị)

```bash
python scripts/add_package.py
```

#### Cách 2: Tạo thủ công

Tạo file YAML trong thư mục `manifests/` với tên `Publisher.AppName.yaml`:

```yaml
packageIdentifier: VNGCorp.Zalo
updateMethod: web
checkUrl: https://www.zalo.me/download
installerUrlPattern: https://res-zalo-pc-stc.zadn.vn/win/Zalo-{version}-win64.msi
architecture: x64
installerType: msi
productCode: "{PRODUCTCODE}"
releaseNotesUrl: https://www.zalo.me
publisher: VNG Corporation
packageName: Zalo
license: Proprietary
shortDescription: Zalo - Nhắn Gửi Yêu Thương
description: |
  Zalo PC - Kết nối với những người thân yêu của bạn.
tags:
  - messenger
  - chat
```

### Các trường cấu hình

- `packageIdentifier`: ID của package theo format `Publisher.AppName`
- `updateMethod`: Phương thức kiểm tra version (`web`, `api`)
- `checkUrl`: URL để kiểm tra phiên bản mới
- `installerUrlPattern`: Pattern URL của installer, `{version}` sẽ được thay thế
- `architecture`: Kiến trúc (`x64`, `x86`, `arm64`)
- `installerType`: Loại installer (`msi`, `exe`, `msix`)
- `productCode`: Product code của MSI installer
- `publisher`: Tên nhà phát hành
- `packageName`: Tên package
- `license`: Loại license
- `shortDescription`: Mô tả ngắn
- `description`: Mô tả chi tiết
- `tags`: Danh sách tags

### Thêm vào workflow

Cập nhật file `.github/workflows/update-packages.yml`, thêm manifest mới vào `matrix.manifest`:

```yaml
strategy:
  matrix:
    manifest:
      - manifests/VNGCorp.Zalo.yaml
      - manifests/YourPublisher.YourApp.yaml
```

## Sử dụng

### Tự động

Workflow sẽ chạy tự động mỗi 6 giờ để kiểm tra phiên bản mới.

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