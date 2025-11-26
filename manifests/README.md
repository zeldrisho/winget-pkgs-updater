# Checkver Configurations

Checkver files define how to detect new package versions.

## File Naming

`{Publisher}.{Package}.checkver.yaml`

## Basic Examples

**GitHub Release:**
```yaml
checkver:
  type: github
  repo: owner/repo

installerUrlTemplate: "https://github.com/owner/repo/releases/download/v{version}/app.exe"
```

**Custom Script:**
```yaml
checkver:
  type: script
  script: |
    $response = Invoke-WebRequest -Uri "https://example.com/version" -UseBasicParsing
    Write-Output $response.Content
  regex: "([\\d\\.]+)"

installerUrlTemplate: "https://example.com/{version}/installer.exe"
```

## Testing

```powershell
pwsh -File scripts/Check-Version.ps1 manifests/YourPackage.checkver.yaml
```

## Documentation

See **[docs/checkver-guide.md](../docs/checkver-guide.md)** for complete reference.
