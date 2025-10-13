# Contributing Guide

Thank you for contributing to WinGet Package Updater!

## Adding New Packages

### Step 1: Check Package Exists

Verify the package exists in microsoft/winget-pkgs:
```
https://github.com/microsoft/winget-pkgs/tree/master/manifests/{first-letter}/{publisher}/{package}
```

Example: `https://github.com/microsoft/winget-pkgs/tree/master/manifests/s/Seelen/SeelenUI`

### Step 2: Find Latest Version

Look at the version folders to understand the version format (e.g., `2.3.12.0`).

### Step 3: Create Checkver Config

Create `manifests/{Publisher}.{Package}.checkver.yaml` with:

```yaml
packageIdentifier: Publisher.Package
manifestPath: manifests/{first-letter}/{publisher}/{package}

checkver:
  type: script
  script: |
    # PowerShell script to detect version
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

### Step 4: Test Locally

```bash
python3 scripts/check_version.py
```

### Step 5: Submit PR

1. Fork this repository
2. Create a new branch
3. Add your checkver config
4. Submit a pull request

## Code Style

- Use clear PowerShell script comments
- Follow existing checkver config format
- Test before submitting

## Questions?

Open an issue or discussion.
