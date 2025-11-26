# GitHub Workflows

GitHub Actions workflows for automating package updates.

## Workflows

### update-packages.yml
Main workflow - checks for updates and creates PRs.

**Trigger:** Every 4 hours or manual

**Runner:** Windows (PowerShell 7.4+)

### cleanup-branches.yml
Removes merged/stale branches from fork.

## Configuration

### Required Secrets

**Settings** → **Secrets and variables** → **Actions**:

| Secret | Required |
|--------|----------|
| `WINGET_PKGS_TOKEN` (GitHub PAT with `repo`, `workflow` scopes) | Yes |
| `WINGET_FORK_REPO` (e.g., `username/winget-pkgs`) | No |

### Manual Trigger

**Actions** → **Update WinGet Packages** → **Run workflow**

## Customization

### Change Schedule

```yaml
schedule:
  - cron: '0 0 * * *'  # Daily at midnight
```

### Change Runner

```yaml
runs-on: ubuntu-latest  # Requires PowerShell 7.4+
```

## See Also

- [../../docs/architecture.md](../../docs/architecture.md) - System architecture
- [../../docs/development.md](../../docs/development.md) - Local testing

