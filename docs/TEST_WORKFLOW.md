# Test Workflow Guide

## Overview

The `test-manifest-checker.yml` workflow provides two testing modes:

1. **Checkver Test Only** (default): Tests version detection without making any changes
2. **Full Integration Test**: Tests the complete flow including fork operations, branch creation, and commits

## Usage

### Mode 1: Checkver Test Only

Tests version detection for all packages or a specific package:

```bash
# Via GitHub UI:
Actions → Test Manifest Checker → Run workflow
- package: (leave empty for all, or enter package name)
- test_fork_commit: false
```

**What it does:**
- Runs `check_version.py` for each checkver config
- Validates version detection logic
- Shows available updates
- **Does not** clone fork, create branches, or make commits

**Use when:**
- Testing new checkver configurations
- Validating version detection logic
- Quick checks without side effects

### Mode 2: Full Integration Test

Tests the complete automation flow with actual fork operations:

```bash
# Via GitHub UI:
Actions → Test Manifest Checker → Run workflow
- package: (enter specific package name, e.g., "Seelen.SeelenUI")
- test_fork_commit: true
```

**What it does:**
1. Runs `check_version.py` to detect version
2. Clones your fork of `microsoft/winget-pkgs`
3. Creates a test branch (e.g., `test/auto-update-Seelen.SeelenUI-2.4.4.0-1234567890`)
4. Runs `update_manifest.py --no-pr` to update manifests
5. Commits changes with test message
6. Pushes branch to your fork
7. **Does not** create a pull request

**Use when:**
- Testing end-to-end automation
- Validating manifest updates
- Checking MSIX signature extraction
- Testing ReleaseNotes fetching
- Verifying fork operations before production

**Requirements:**
- `WINGET_PKGS_TOKEN` secret must be configured
- You must have a fork of `microsoft/winget-pkgs`

## Automatic Triggers

The workflow also runs automatically on:
- Pull requests that modify `manifests/**.yaml`
- Pull requests that modify `scripts/check_version.py`
- Pull requests that modify `scripts/update_manifest.py`

In automatic mode, only checkver testing is performed (no fork operations).

## Workflow Output

### Checkver Test Mode
```
=== Testing Checkver Configurations ===

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Testing: manifests/Seelen.SeelenUI.checkver.yaml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Package: Seelen.SeelenUI
Current version: 2.4.3.0
Latest version: 2.4.4.0
Update available: 2.4.3.0 → 2.4.4.0

✅ SUCCESS: manifests/Seelen.SeelenUI.checkver.yaml
```

### Fork Commit Test Mode
```
=== Cloning winget-pkgs fork ===
GitHub username: zeldrisho
✅ Fork cloned successfully

=== Creating test branch and commit ===
Package: Seelen.SeelenUI
Version: 2.4.4.0
Branch: test/auto-update-Seelen.SeelenUI-2.4.4.0-1234567890

Running update_manifest.py...
✅ Successfully updated manifests in /tmp/winget-pkgs

=== Changes ===
 manifests/s/Seelen/SeelenUI/2.4.4.0/Seelen.SeelenUI.yaml | 2 +-
 manifests/s/Seelen/SeelenUI/2.4.4.0/Seelen.SeelenUI.installer.yaml | 4 ++--
 2 files changed, 3 insertions(+), 3 deletions(-)

Pushing to fork...
✅ Test branch created and pushed: test/auto-update-Seelen.SeelenUI-2.4.4.0-1234567890
View at: https://github.com/zeldrisho/winget-pkgs/tree/test/auto-update-Seelen.SeelenUI-2.4.4.0-1234567890
```

## Test Branch Cleanup

Test branches are created with `test/` prefix. To clean them up:

```bash
# List all test branches
gh api repos/{username}/winget-pkgs/branches --jq '.[] | select(.name | startswith("test/")) | .name'

# Delete a specific test branch
gh api -X DELETE repos/{username}/winget-pkgs/git/refs/heads/test/auto-update-Seelen.SeelenUI-2.4.4.0-1234567890

# Or use git directly
git push origin --delete test/auto-update-Seelen.SeelenUI-2.4.4.0-1234567890
```

## Comparing with Production Workflow

| Feature | Test Workflow | Production Workflow |
|---------|--------------|---------------------|
| Version Detection | ✅ Yes | ✅ Yes |
| Manifest Update | ✅ Yes (with flag) | ✅ Yes |
| Branch Creation | ✅ Yes (with flag) | ✅ Yes |
| Commit & Push | ✅ Yes (with flag) | ✅ Yes |
| Create PR | ❌ No | ✅ Yes |
| PR Duplicate Check | ❌ Skipped | ✅ Yes |
| Schedule | ⚙️ Manual only | ⏰ Cron (daily) |

## Troubleshooting

### Error: "Version info file not found"

The checkver test failed. Check the checkver configuration:
- Verify the URL is accessible
- Check regex patterns match the response
- Ensure PowerShell script syntax is correct

### Error: "WINGET_PKGS_TOKEN environment variable not set"

Configure the secret in your repository:
1. Go to Settings → Secrets and variables → Actions
2. Add `WINGET_PKGS_TOKEN` with your GitHub Personal Access Token
3. Token needs `repo` scope for fork operations

### Error: "Failed to clone repository"

Check:
- Token has correct permissions
- You have a fork of `microsoft/winget-pkgs`
- Token is not expired

### No changes to commit

The manifest was already up to date. This can happen if:
- Version was already updated manually
- Previous test run already updated the fork
- The installer URL or SHA256 hasn't changed

## Best Practices

1. **Test checkver first**: Always run checkver-only test before fork commit test
2. **One package at a time**: Use fork commit test for one package to avoid clutter
3. **Clean test branches**: Delete test branches after verification
4. **Monitor rate limits**: GitHub API has rate limits, avoid excessive testing
5. **Verify changes**: Review the test branch before running production workflow

## Examples

### Example 1: Test new checkver config
```bash
# 1. Create new checkver config
vim manifests/Example.App.checkver.yaml

# 2. Test it
Actions → Test Manifest Checker → Run workflow
- package: Example.App
- test_fork_commit: false

# 3. If success, test full flow
Actions → Test Manifest Checker → Run workflow
- package: Example.App
- test_fork_commit: true

# 4. Verify test branch
Visit: https://github.com/{username}/winget-pkgs/branches/all?query=test/
```

### Example 2: Debug MSIX signature issues
```bash
# Enable fork commit test to see actual extraction
Actions → Test Manifest Checker → Run workflow
- package: Seelen.SeelenUI
- test_fork_commit: true

# Check logs for signature calculation
# View the updated installer manifest in test branch
```

### Example 3: Test all packages quickly
```bash
# Test all checkver configs without fork operations
Actions → Test Manifest Checker → Run workflow
- package: (empty)
- test_fork_commit: false
```

## Integration with Production

Once test workflow succeeds:

1. **Manual trigger**: Run production workflow manually for specific package
2. **Scheduled run**: Wait for next scheduled run (daily at 02:00 UTC)
3. **Monitor**: Check production workflow creates PR successfully

The test workflow uses the same scripts as production, ensuring consistency.

## Technical Details

### Fork Commit Test Implementation

```yaml
- name: Clone winget-pkgs fork
  if: github.event.inputs.test_fork_commit == 'true'
  env:
    GH_TOKEN: ${{ secrets.WINGET_PKGS_TOKEN }}
  run: |
    username=$(gh api user -q .login)
    git clone "https://x-access-token:${GH_TOKEN}@github.com/${username}/winget-pkgs.git" /tmp/winget-pkgs

- name: Create test branch and commit
  if: github.event.inputs.test_fork_commit == 'true'
  run: |
    cd /tmp/winget-pkgs
    git checkout -b "test/auto-update-${package_id}-${new_version}-$(date +%s)"
    
    python3 scripts/update_manifest.py "$config_path" "$version_info_file" --no-pr --fork-path /tmp/winget-pkgs
    
    git add .
    git commit -m "test: Update ${package_id} to ${new_version}"
    git push -u origin "$branch_name"
```

### CLI Arguments

The `update_manifest.py` script accepts:

```
update_manifest.py <checkver_config> <version_info> [--no-pr] [--fork-path PATH]

Arguments:
  checkver_config  Path to checkver YAML config
  version_info     Path to version info JSON file
  --no-pr          Skip PR creation (for testing)
  --fork-path      Use existing fork clone at PATH
```

## See Also

- [SETUP.md](../SETUP.md) - Initial setup and token configuration
- [QUICKSTART.md](../QUICKSTART.md) - Quick start guide
- [RELEASENOTES_AUTOFETCH.md](RELEASENOTES_AUTOFETCH.md) - ReleaseNotes auto-fetch feature
