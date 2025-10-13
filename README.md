# winget-pkgs-updater

Tự động tạo Pull Request lên [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) khi phát hiện phiên bản mới của các ứng dụng.

## Tính năng

- ✅ Tự động kiểm tra phiên bản mới của các ứng dụng
- ✅ Tạo manifest theo đúng format của microsoft/winget-pkgs
- ✅ Tự động tạo Pull Request sử dụng tài khoản GitHub của bạn
- ✅ Hỗ trợ nhiều ứng dụng với cấu hình độc lập
- ✅ Chạy định kỳ bằng GitHub Actions

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
│   └── VNGCorp.Zalo.yaml
├── scripts/                       # Scripts Python
│   ├── check_version.py           # Kiểm tra version mới
│   ├── generate_manifest.py       # Tạo manifest files
│   └── requirements.txt           # Python dependencies
└── README.md
```

## Tham khảo

Dự án được lấy cảm hứng từ:

- [SpecterShell/Dumplings](https://github.com/SpecterShell/Dumplings)
- [vedantmgoyal9/winget-pkgs-automation](https://github.com/vedantmgoyal9/winget-pkgs-automation)
- [ScoopInstaller/GithubActions](https://github.com/ScoopInstaller/GithubActions)

## License

GPL-3.0 License - Xem file [LICENSE](LICENSE) để biết thêm chi tiết.