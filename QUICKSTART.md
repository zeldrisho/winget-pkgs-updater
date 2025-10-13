# Quick Start Guide | Hướng Dẫn Nhanh

## English

### What is this?

This project automatically creates Pull Requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when it detects new versions of applications.

### Quick Setup (5 minutes)

1. **Fork this repository**
   - Click "Fork" button at the top right

2. **Fork microsoft/winget-pkgs**
   - Go to https://github.com/microsoft/winget-pkgs
   - Click "Fork" button
   - Note your fork URL (e.g., `yourusername/winget-pkgs`)

3. **Create Personal Access Token**
   - Go to https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo` and `workflow`
   - Copy the token

4. **Add Secret to Your Repository**
   - Go to your forked repo → Settings → Secrets and variables → Actions
   - Add secret:
     - Name: `WINGET_PKGS_TOKEN`
     - Value: Your personal access token
   - Note: Fork URL is auto-detected from your GitHub username

5. **Enable GitHub Actions**
   - Go to Actions tab
   - Click "I understand my workflows, go ahead and enable them"

### Test It!

1. Go to Actions tab
2. Click "Update WinGet Packages"
3. Click "Run workflow"
4. Watch it run!

### Next Steps

- Read [SETUP.md](SETUP.md) for detailed setup
- Read [CONTRIBUTING.md](CONTRIBUTING.md) to add more packages
- Check the workflow runs in the Actions tab

---

## Tiếng Việt

### Đây là gì?

Dự án này tự động tạo Pull Request lên [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) khi phát hiện phiên bản mới của các ứng dụng.

### Cài Đặt Nhanh (5 phút)

1. **Fork repository này**
   - Click nút "Fork" ở góc trên bên phải

2. **Fork microsoft/winget-pkgs**
   - Vào https://github.com/microsoft/winget-pkgs
   - Click nút "Fork"
   - Ghi nhớ URL fork của bạn (ví dụ: `tendangnguoidung/winget-pkgs`)

3. **Tạo Personal Access Token**
   - Vào https://github.com/settings/tokens
   - Click "Generate new token (classic)"
   - Chọn quyền: `repo` và `workflow`
   - Copy token

4. **Thêm Secret vào Repository của bạn**
   - Vào repo đã fork → Settings → Secrets and variables → Actions
   - Thêm secret:
     - Name: `WINGET_PKGS_TOKEN`
     - Value: Token vừa tạo
   - Lưu ý: Fork URL tự động detect từ GitHub username

5. **Kích hoạt GitHub Actions**
   - Vào tab Actions
   - Click "I understand my workflows, go ahead and enable them"

### Thử Nghiệm!

1. Vào tab Actions
2. Click "Update WinGet Packages"
3. Click "Run workflow"
4. Xem nó chạy!

### Bước Tiếp Theo

- Đọc [SETUP.md](SETUP.md) để biết hướng dẫn chi tiết
- Đọc [CONTRIBUTING.md](CONTRIBUTING.md) để thêm packages mới
- Kiểm tra workflow runs trong tab Actions

---

## Workflow Overview | Tổng Quan Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions Workflow                   │
│                    (Runs every 6 hours)                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: Check Version                                       │
│  - Read manifest configuration (VNGCorp.Zalo.yaml)          │
│  - Scrape download page for latest version                  │
│  - Compare with current version                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  New version?   │
                    └─────────────────┘
                         │         │
                    No   │         │  Yes
                         │         │
                      Exit         ▼
                    ┌─────────────────────────────────────┐
                    │  Step 2: Generate Manifests          │
                    │  - Download installer                │
                    │  - Compute SHA256 hash               │
                    │  - Generate 3 YAML files             │
                    │    * Version manifest                │
                    │    * Installer manifest              │
                    │    * Locale manifest                 │
                    └─────────────────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  Step 3: Create Branch              │
                    │  - Checkout your winget-pkgs fork   │
                    │  - Create new branch                │
                    │  - Copy manifest files              │
                    │  - Commit and push                  │
                    └─────────────────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────────────┐
                    │  Step 4: Create Pull Request        │
                    │  - Use your GitHub token            │
                    │  - Create PR to microsoft/winget-pkgs│
                    │  - Add description and metadata     │
                    └─────────────────────────────────────┘
                                   │
                                   ▼
                              ┌─────────┐
                              │  Done!  │
                              └─────────┘
```

## Support | Hỗ Trợ

- **English**: See [SETUP.md](SETUP.md) and [CONTRIBUTING.md](CONTRIBUTING.md)
- **Tiếng Việt**: Xem [SETUP.md](SETUP.md) và [CONTRIBUTING.md](CONTRIBUTING.md)
- **Issues**: Open an issue in this repository
- **Questions**: Check the workflow logs in Actions tab
