# Quick Start Guide# Quick Start Guide# Quick Start Guide | Hướng Dẫn Nhanh



Get up and running in 5 minutes.



## What is this?Get up and running in 5 minutes.## English



This project automatically creates Pull Requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when it detects new versions of applications.



## Prerequisites## Prerequisites### What is this?



- GitHub account

- Fork of [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)

- GitHub accountThis project automatically creates Pull Requests to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) when it detects new versions of applications.

## Setup Steps

- Fork of [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)

### 1. Create Personal Access Token

### Quick Setup (5 minutes)

1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)

2. Click **"Generate new token (classic)"**## Setup Steps

3. Name: `WinGet Packages Updater`

4. Select scopes:1. **Fork this repository**

   - ✅ `repo` (all sub-scopes)

   - ✅ `workflow`### 1. Create Personal Access Token   - Click "Fork" button at the top right

5. Click **"Generate token"**

6. **Copy the token** (you won't see it again!)



### 2. Add Secret to Repository1. Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens)2. **Fork microsoft/winget-pkgs**



1. Go to your fork's **Settings → Secrets and variables → Actions**2. Click **"Generate new token (classic)"**   - Go to https://github.com/microsoft/winget-pkgs

2. Click **"New repository secret"**

3. Name: `WINGET_PKGS_TOKEN`3. Name: `WinGet Packages Updater`   - Click "Fork" button

4. Value: Paste your token from step 1

5. Click **"Add secret"**4. Select scopes:   - Note your fork URL (e.g., `yourusername/winget-pkgs`)



### 3. Run Workflow   - ✅ `repo` (all sub-scopes)



1. Go to **Actions** tab   - ✅ `workflow`3. **Create Personal Access Token**

2. Select **"Update WinGet Packages"** workflow

3. Click **"Run workflow"** → **"Run workflow"**5. Click **"Generate token"**   - Go to https://github.com/settings/tokens

4. Wait for the workflow to complete

6. **Copy the token** (you won't see it again!)   - Click "Generate new token (classic)"

### 4. Check Results

   - Select scopes: `repo` and `workflow`

- Check workflow logs for update details

- Check PRs at: `https://github.com/microsoft/winget-pkgs/pulls?q=author:YOUR_USERNAME`### 2. Add Secret to Repository   - Copy the token



## Add Your First Package



1. Create `manifests/{Publisher}.{Package}.checkver.yaml`1. Go to your fork's **Settings → Secrets and variables → Actions**4. **Add Secret to Your Repository**

2. Follow the examples in README.md

3. Commit and push2. Click **"New repository secret"**   - Go to your forked repo → Settings → Secrets and variables → Actions

4. Run workflow again

3. Name: `WINGET_PKGS_TOKEN`   - Add secret:

## Common Issues

4. Value: Paste your token from step 1     - Name: `WINGET_PKGS_TOKEN`

**Token error**: Make sure the secret name is exactly `WINGET_PKGS_TOKEN`

5. Click **"Add secret"**     - Value: Your personal access token

**Package not found**: Check `manifestPath` points to correct location in microsoft/winget-pkgs

   - Note: Fork URL is auto-detected from your GitHub username

**PR already exists**: This is normal - duplicate prevention is working

### 3. Run Workflow

## Need Help?

5. **Enable GitHub Actions**

Check the main [README.md](README.md) for detailed documentation.

1. Go to **Actions** tab   - Go to Actions tab

2. Select **"Update WinGet Packages"** workflow   - Click "I understand my workflows, go ahead and enable them"

3. Click **"Run workflow"** → **"Run workflow"**

4. Wait for the workflow to complete### Test It!



### 4. Check Results1. Go to Actions tab

2. Click "Update WinGet Packages"

- Check workflow logs for update details3. Click "Run workflow"

- Check PRs at: `https://github.com/microsoft/winget-pkgs/pulls?q=author:YOUR_USERNAME`4. Watch it run!



## Add Your First Package### Next Steps



1. Create `manifests/{Publisher}.{Package}.checkver.yaml`- Read [SETUP.md](SETUP.md) for detailed setup

2. Follow the examples in README.md- Read [CONTRIBUTING.md](CONTRIBUTING.md) to add more packages

3. Commit and push- Check the workflow runs in the Actions tab

4. Run workflow again

---

## Common Issues

## Tiếng Việt

**Token error**: Make sure the secret name is exactly `WINGET_PKGS_TOKEN`

### Đây là gì?

**Package not found**: Check `manifestPath` points to correct location in microsoft/winget-pkgs

Dự án này tự động tạo Pull Request lên [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs) khi phát hiện phiên bản mới của các ứng dụng.

**PR already exists**: This is normal - duplicate prevention is working

### Cài Đặt Nhanh (5 phút)

## Need Help?

1. **Fork repository này**

Check the main [README.md](README.md) for detailed documentation.   - Click nút "Fork" ở góc trên bên phải


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
