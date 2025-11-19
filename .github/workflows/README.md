# GitHub Workflows

This directory contains GitHub Actions workflows for automating package updates.

## Workflows

### update-packages.yml

**Main workflow** - Automatically checks for package updates and creates pull requests.

**Trigger:**
- Scheduled: Every 4 hours (at :20 past the hour)
- Manual: Via workflow dispatch

**What it does:**
1. Finds all checkver files in `manifests/`
2. Checks each package for new versions
3. Checks for existing PRs (skips if OPEN/MERGED)
4. Downloads installers and calculates SHA256
5. Updates manifest files
6. Creates pull requests to microsoft/winget-pkgs

**Runner:** Windows (for PowerShell 7.4+ compatibility)

**Environment variables:**
- `GITHUB_TOKEN` or `GH_TOKEN` - GitHub token (required)
- `WINGET_FORK_REPO` - Your fork of winget-pkgs (optional)
- `GITHUB_REPOSITORY_OWNER` - Auto-set by GitHub Actions

### cleanup-branches.yml

**Branch cleanup** - Removes old branches from fork repository.

**Trigger:**
- Scheduled or manual

**What it does:**
- Deletes merged branches to keep fork clean
- Removes stale branches after PR closure

## Workflow Configuration

### Required Secrets

Set these in **Settings** → **Secrets and variables** → **Actions**:

| Secret | Description | Required |
|--------|-------------|----------|
| `WINGET_PKGS_TOKEN` | GitHub PAT with `repo`, `workflow` scopes | Yes |
| `WINGET_FORK_REPO` | Your fork repo (e.g., `username/winget-pkgs`) | No (defaults to `{owner}/winget-pkgs`) |

### Manual Trigger

To manually run the update workflow:

1. Go to **Actions** → **Update WinGet Packages**
2. Click **Run workflow**
3. (Optional) Specify a package name to update only that package
4. Click **Run workflow**

## Workflow Behavior

### PR Gate Logic

The workflow implements smart PR management:

| PR State | Action |
|----------|--------|
| 🟢 **OPEN** | Skip - Already submitted |
| 🟣 **MERGED** | Skip - Already accepted |
| ⚪ **CLOSED** | Check branch existence:<br>- Branch exists → Skip<br>- Branch deleted → Retry |

This prevents:
- Duplicate PRs
- Spamming microsoft/winget-pkgs
- Overriding upstream decisions

### Error Handling

- Git push operations use exponential backoff retry (4 attempts)
- Failed packages don't block others (fail-fast: false)
- Errors are logged in workflow output

## Customization

### Change Schedule

Edit `update-packages.yml`:

```yaml
on:
  schedule:
    - cron: '20 */4 * * *'  # Every 4 hours
    # Change to:
    - cron: '0 0 * * *'     # Daily at midnight
```

### Change Runner

For Linux runners (if PowerShell is available):

```yaml
jobs:
  update:
    runs-on: ubuntu-latest  # Change from windows-latest
```

Note: Requires PowerShell 7.4+ to be installed on runner.

### Add Notifications

Add a notification step:

```yaml
- name: Notify on failure
  if: failure()
  uses: some/notification-action@v1
  with:
    message: "Package update failed"
```

## Monitoring

### Workflow Runs

View all workflow runs:
- Go to **Actions** tab
- Click on workflow name
- See history of all runs

### Workflow Logs

View detailed logs:
- Click on a specific run
- Expand job steps to see output
- Download logs for debugging

### Workflow Status

Get workflow status:
```bash
gh workflow view "Update WinGet Packages"
gh run list --workflow=update-packages.yml
```

## Troubleshooting

### Workflow not running

- Check that workflows are enabled in your fork
- Verify schedule syntax in YAML
- Check repository permissions

### Authentication failures

- Verify `WINGET_PKGS_TOKEN` is set correctly
- Check token has `repo` and `workflow` scopes
- Ensure token hasn't expired

### Package updates failing

- Check package checkver configuration
- Test locally: `pwsh -File scripts/Check-Version.ps1 manifests/Package.checkver.yaml`
- Review workflow logs for errors

## Best Practices

1. **Test locally first** - Always test checkver configs before committing
2. **Monitor workflow runs** - Check Actions tab regularly
3. **Handle failures** - Investigate and fix failed updates promptly
4. **Keep fork synced** - Regularly sync your winget-pkgs fork with upstream
5. **Use secrets** - Never commit tokens or credentials

## See Also

- [../docs/architecture.md](../docs/architecture.md) - System architecture
- [../docs/development.md](../docs/development.md) - Local development
- [GitHub Actions documentation](https://docs.github.com/en/actions)
