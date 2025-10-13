# Setup Guide

This guide will help you set up the WinGet Packages Updater to automatically create Pull Requests to microsoft/winget-pkgs.

## Prerequisites

- A GitHub account
- Basic knowledge of GitHub Actions and YAML

## Step-by-Step Setup

### 1. Fork This Repository

1. Click the "Fork" button at the top right of this repository
2. Choose your account as the destination

### 2. Fork microsoft/winget-pkgs

This is necessary because GitHub PRs from Actions require a fork:

1. Go to [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)
2. Click the "Fork" button
3. Make note of your fork URL (e.g., `yourusername/winget-pkgs`)

### 3. Create Personal Access Token (PAT)

The token is used to create branches and PRs on your behalf:

1. Go to [GitHub Settings → Developer settings → Personal access tokens → Tokens (classic)](https://github.com/settings/tokens)
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a descriptive name (e.g., "WinGet Packages Updater")
4. Set expiration (recommend: 90 days or longer)
5. Select the following scopes:
   - ✅ **repo** (Full control of private repositories)
   - ✅ **workflow** (Update GitHub Action workflows)
6. Click "Generate token"
7. **Important:** Copy the token and save it securely (you won't see it again!)

### 4. Configure Repository Secrets

Add the following secret to your forked repository:

1. Go to your forked repository's Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add this secret:

   **Secret: WINGET_PKGS_TOKEN**
   - Name: `WINGET_PKGS_TOKEN`
   - Value: The Personal Access Token you created above
   
   Note: Your fork URL is automatically detected from your GitHub username. The workflow will clone `https://github.com/YOUR_USERNAME/winget-pkgs`.

### 5. Enable GitHub Actions

1. Go to the "Actions" tab in your repository
2. If prompted, click "I understand my workflows, go ahead and enable them"

### 6. Test the Workflow

Run a manual test:

1. Go to Actions → "Update WinGet Packages"
2. Click "Run workflow"
3. Leave the package field empty to test all packages
4. Click "Run workflow"
5. Wait for the workflow to complete

## Configuration

### Understanding the Workflow

The workflow runs:
- **Automatically**: Every 6 hours
- **Manually**: When you trigger it from the Actions tab

### Adding New Packages

To monitor additional applications:

#### Option 1: Use the Helper Script (Recommended)

```bash
# Clone your repository locally
git clone https://github.com/yourusername/winget-pkgs-updater
cd winget-pkgs-updater

# Run the helper script
python scripts/add_package.py

# Follow the prompts to configure your package
```

#### Option 2: Create Manually

1. Create a new file in `manifests/` named `Publisher.AppName.yaml`
2. Follow the template in `manifests/README.md`
3. Add your new manifest to the workflow matrix in `.github/workflows/update-packages.yml`:

```yaml
strategy:
  matrix:
    manifest:
      - manifests/VNGCorp.Zalo.yaml
      - manifests/YourPublisher.YourApp.yaml  # Add this line
```

4. Commit and push your changes

### Testing Your Configuration

Before relying on the automated workflow, test your manifest:

```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Test version checking
python scripts/check_version.py manifests/YourPublisher.YourApp.yaml

# Test manifest generation (requires a valid version and URL)
python scripts/generate_manifest.py \
  manifests/YourPublisher.YourApp.yaml \
  1.0.0 \
  https://example.com/installer.msi \
  /tmp/test-manifests
```

## Troubleshooting

### Workflow Not Running

- Check that GitHub Actions is enabled in repository settings
- Verify secrets are properly configured
- Check the Actions tab for error messages

### PR Not Created

- Ensure `WINGET_PKGS_TOKEN` has correct permissions (`repo` + `workflow`)
- Verify your fork exists at: `https://github.com/YOUR_USERNAME/winget-pkgs`
- Check that your fork of winget-pkgs is up to date with upstream

### Version Not Detected

- Verify the `checkUrl` in your manifest is correct
- Check the workflow logs for error messages
- The website might be blocking automated requests
- Consider implementing custom version detection logic

### Invalid Manifest Format

- Run the test script to validate: `python scripts/test_manifest.py`
- Check the [WinGet manifest schema](https://github.com/microsoft/winget-pkgs/tree/master/doc/manifest/schema/1.6.0)
- Ensure YAML syntax is correct

## Maintenance

### Keeping Your Fork Updated

Your microsoft/winget-pkgs fork should be periodically synced:

1. Go to your fork: `https://github.com/yourusername/winget-pkgs`
2. Click "Sync fork" → "Update branch"
3. Or use Git:
   ```bash
   git clone https://github.com/yourusername/winget-pkgs
   cd winget-pkgs
   git remote add upstream https://github.com/microsoft/winget-pkgs
   git fetch upstream
   git checkout master
   git merge upstream/master
   git push origin master
   ```

### Updating PAT

If your Personal Access Token expires:

1. Create a new token (follow step 3 above)
2. Update the `WINGET_PKGS_TOKEN` secret in repository settings

## Advanced Configuration

### Changing Check Frequency

Edit `.github/workflows/update-packages.yml`:

```yaml
schedule:
  # Every 6 hours (current)
  - cron: '0 */6 * * *'
  
  # Every 12 hours
  # - cron: '0 */12 * * *'
  
  # Daily at midnight UTC
  # - cron: '0 0 * * *'
```

### Custom Version Detection

For complex version detection needs, modify `scripts/check_version.py`:

```python
def get_latest_version_from_web(check_url: str) -> Optional[str]:
    # Add your custom logic here
    pass
```

## Support

If you encounter issues:

1. Check the [workflow logs](../../actions) for error messages
2. Review this setup guide
3. Check [microsoft/winget-pkgs documentation](https://github.com/microsoft/winget-pkgs)
4. Open an issue in this repository

## Security Notes

- Never commit your Personal Access Token
- Use repository secrets for all sensitive data
- Regularly rotate your PAT
- Review permissions before creating tokens
- Monitor the Actions tab for unexpected activity
