# Package Checkver Configuration Guide# WinGet Package Checkver Configurations



This directory contains checkver configuration files for package version checking.This directory contains checkver configuration files that tell the updater how to check for new package versions.



## File Naming## How It Works



`{Publisher}.{Package}.checkver.yaml`1. **Checkver files** in this repo define how to detect new versions

2. **GitHub Actions** periodically checks for updates

Examples:3. **When found**, it:

- `VNGCorp.Zalo.checkver.yaml`   - Forks/clones `microsoft/winget-pkgs`

- `Seelen.SeelenUI.checkver.yaml`   - Fetches the latest manifest

   - Updates version and SHA256

## Configuration Format   - Creates a PR to `microsoft/winget-pkgs`



### Required Fields## File Structure



```yaml```

packageIdentifier: Publisher.Packagemanifests/

manifestPath: manifests/{first-letter}/{publisher}/{package}├── README.md

├── Publisher.Package.checkver.yaml

checkver:└── VNGCorp.Zalo.checkver.yaml

  type: script```

  script: |

    # PowerShell script to get versionEach checkver file contains only the configuration needed to check for updates.

  regex: "([\\d\\.]+)"

## Checkver Configuration Format

installerUrlTemplate: "https://example.com/download/{version}/installer.exe"

```### Example: VNGCorp.Zalo.checkver.yaml



### manifestPath Structure```yaml

# Package identifier

The path follows microsoft/winget-pkgs structure:packageIdentifier: VNGCorp.Zalo

- `manifests/{first-letter}/{publisher}/{package}`

- First letter is lowercase first character of publisher name# Path in microsoft/winget-pkgs repository

manifestPath: manifests/v/VNGCorp/Zalo

**Examples:**

- `Seelen.SeelenUI` → `manifests/s/Seelen/SeelenUI`# Version checking method

- `VNGCorp.Zalo` → `manifests/v/VNGCorp/Zalo`checkver:

- `Google.Chrome` → `manifests/g/Google/Chrome`  type: script  # or 'web' for simple scraping

  script: |

**How to find the correct path:**    # PowerShell script to get download URL

1. Go to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs/tree/master/manifests)    try {

2. Navigate to the first letter folder (e.g., `s` for Seelen)      $response = Invoke-WebRequest -Uri "https://zalo.me/download/zalo-pc" -MaximumRedirection 0

3. Find the publisher folder (e.g., `Seelen`)      if ($response.Headers.Location) {

4. Find the package folder (e.g., `SeelenUI`)        Write-Output $response.Headers.Location.OriginalString

5. Note the version folders inside (e.g., `2.3.12.0`)      }

    } catch {

## Examples      if ($_.Exception.Response.Headers.Location) {

        Write-Output $_.Exception.Response.Headers.Location.OriginalString

### Method 1: Web Scraping (HTTP Redirect)      }

    }

For packages with download URLs that redirect to versioned URLs.  regex: ZaloSetup-([\d\.]+)\.exe  # Extract version from URL



```yaml# Installer URL template for downloading and calculating SHA256

packageIdentifier: VNGCorp.ZaloinstallerUrlTemplate: https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-{version}.exe

manifestPath: manifests/v/VNGCorp/Zalo```



checkver:### Alternative: Simple Web Scraping

  type: script

  script: |```yaml

    $url = "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup.exe"packageIdentifier: Publisher.Package

    $response = Invoke-WebRequest -Uri $url -MaximumRedirection 0 -ErrorAction SilentlyContinuemanifestPath: manifests/p/Publisher/Package

    if ($response.Headers.Location) {

      $redirectUrl = $response.Headers.Locationcheckver:

      if ($redirectUrl -match "ZaloSetup-([\\d\\.]+)\\.exe") {  type: web

        Write-Output $matches[1]  checkUrl: https://example.com/download

      }  regex: Package-v?([\d\.]+)\.exe

    }

  regex: "([\\d\\.]+)"installerUrlTemplate: https://example.com/downloads/Package-{version}.exe

```

installerUrlTemplate: "https://res-zaloapp-aka.zdn.vn/win/ZaloSetup-{version}.exe"

```## Adding a New Package



### Method 2: GitHub Releases API1. Create a new checkver file: `manifests/Publisher.Package.checkver.yaml`

2. Define the package identifier and manifest path

For open-source projects hosted on GitHub.3. Configure the version checking method

4. Test locally:

```yaml   ```bash

packageIdentifier: Seelen.SeelenUI   python scripts/check_version.py manifests/Publisher.Package.checkver.yaml

manifestPath: manifests/s/Seelen/SeelenUI   ```

5. Add to GitHub Actions workflow matrix

checkver:

  type: script## PR Format

  script: |

    $response = Invoke-RestMethod -Uri "https://api.github.com/repos/eythaann/Seelen-UI/releases/latest"When a new version is detected, the automation will:

    if ($response.tag_name) {

      $version = $response.tag_name -replace '^v', ''1. Fork `microsoft/winget-pkgs` (if not already forked)

      Write-Output $version2. Create a new branch: `PackageIdentifier-version`

    }3. Update manifest files with new version and SHA256

  regex: "([\\d\\.]+)"4. Create PR with:

   - **Title**: `New version: VNGCorp.Zalo version 25.8.3`

installerUrlTemplate: "https://github.com/eythaann/Seelen-UI/releases/download/v{version}/Seelen.UI_{version}_x64-setup.exe"   - **Body**: `Automated by [zeldrisho/winget-pkgs-updater](https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/123456789) in workflow run #123456789.`

```   

   The workflow run link is clickable, making it easy for Microsoft reviewers to verify the automation.

### Method 3: HTML Scraping

## Benefits of This Approach

For packages with version info in HTML pages.

✅ **Minimal storage** - Only checkver configs in this repo

```yaml✅ **Always up-to-date** - Fetches latest manifest from microsoft/winget-pkgs

packageIdentifier: Example.App✅ **Automatic SHA256** - Downloads installer and calculates hash

manifestPath: manifests/e/Example/App✅ **Clean PRs** - Creates proper branches and descriptive PR messages

✅ **Scalable** - Easy to add more packages

checkver:

  type: script## References

  script: |

    $html = Invoke-WebRequest -Uri "https://example.com/download"- [Microsoft WinGet Packages](https://github.com/microsoft/winget-pkgs)

    if ($html.Content -match "Version ([\\d\\.]+)") {- [WinGet Manifest Schema](https://github.com/microsoft/winget-cli/tree/master/schemas)

      Write-Output $matches[1]
    }
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/downloads/app-{version}.exe"
```

## Testing Your Configuration

Run locally:

```bash
python3 scripts/check_version.py
```

This will test all checkver configs and show detected versions.

## Version Format

**Important**: The version format must match what's in microsoft/winget-pkgs.

Examples:
- `2.3.12.0` (4 parts) - not `2.3.12`
- `25.10.2` (3 parts) - not `25.10.2.0`

Check existing manifests to confirm the version format:
`https://github.com/microsoft/winget-pkgs/tree/master/manifests/{path}`

## Troubleshooting

### Version not detected
- Test the PowerShell script manually in a PowerShell terminal
- Check if the regex pattern matches the output
- Ensure the website/API is accessible

### Wrong version format
- Check existing manifests in microsoft/winget-pkgs
- Adjust the regex or add/remove version parts

### Installer URL incorrect
- Verify the `installerUrlTemplate` with actual download URL
- Use `{version}` placeholder where version appears in URL

## Need Help?

See the main [README.md](../README.md) for more information.
