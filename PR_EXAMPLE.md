# 📝 Example Pull Request

This is what the automated PR will look like in microsoft/winget-pkgs:

---

## Example PR

**To:** microsoft/winget-pkgs

**Title:**
```
New version: VNGCorp.Zalo version 25.10.2
```

**Body:**
```markdown
Automated by [zeldrisho/winget-pkgs-updater](https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/8234567890) in workflow run #42.
```

**Note:** 
- Run number `#42` is the sequential workflow run count (automatically pulled from `$GITHUB_RUN_NUMBER`)
- The link uses the unique run ID `8234567890` (from `$GITHUB_RUN_ID`) to identify the exact workflow execution

### Visual Appearance

In GitHub, it will render as:

> **New version: VNGCorp.Zalo version 25.10.2**
> 
> Automated by [zeldrisho/winget-pkgs-updater](https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/8234567890) in workflow run #8234567890.

Where:
- ✅ `zeldrisho/winget-pkgs-updater` is a **clickable link** to your repo
- ✅ The link goes to the **specific workflow run** that created the PR
- ✅ Reviewers can click to see logs, verify automation, check what was updated

### Files Changed

```diff
manifests/v/VNGCorp/Zalo/25.10.2/
├── VNGCorp.Zalo.installer.yaml
├── VNGCorp.Zalo.locale.vi-VN.yaml
└── VNGCorp.Zalo.yaml
```

Each file will show:
- ✅ Updated `PackageVersion: 25.10.2`
- ✅ Updated `InstallerUrl` with new version
- ✅ Updated `InstallerSha256` with calculated hash
- ✅ Updated `DisplayName` if applicable

### Branch Name
```
VNGCorp.Zalo-25.10.2
```

### Commit Message
```
New version: VNGCorp.Zalo version 25.10.2
```

---

## Why This Format?

1. **Title follows Microsoft's convention**
   - Clear what package is being updated
   - Clear what version is being added

2. **Body provides traceability**
   - Link to automation source
   - Link to specific workflow run
   - Run number for quick reference

3. **Easy verification**
   - Reviewers click link → see workflow logs
   - Can verify checksums, URLs, everything automated
   - Transparent process

4. **Professional appearance**
   - Clean, minimal text
   - Follows PR best practices
   - Easy to batch-review multiple PRs

---

## Example in Action

When Microsoft reviewers see your PR:

1. They see: `New version: VNGCorp.Zalo version 25.10.2`
2. They click the link in body
3. They see your workflow logs showing:
   - Version detected: 25.10.2
   - Installer downloaded
   - SHA256 calculated: `3324E8A9EA0960C4...`
   - Manifest updated
   - Tests passed
4. They approve! ✅

---

## Compare to Manual PRs

**Manual PR:**
```
Update Zalo

Updated to latest version
```
❌ Unclear what version
❌ No verification info
❌ Takes longer to review

**Automated PR:**
```
New version: VNGCorp.Zalo version 25.10.2

Automated by [repo-link] in workflow run #123456789.
```
✅ Clear version
✅ Full verification via link
✅ Fast review

---

This format makes your PRs stand out as **professional**, **transparent**, and **trustworthy**! 🌟
