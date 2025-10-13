# 🔧 Technical Details - Workflow Run Number vs Run ID

## How It Works

### GitHub Actions Environment Variables

When a GitHub Actions workflow runs, it automatically provides several environment variables:

```bash
GITHUB_RUN_NUMBER=42         # Sequential number (1, 2, 3, ...) - human readable
GITHUB_RUN_ID=8234567890     # Unique ID for this workflow run - for URLs
GITHUB_REPOSITORY=owner/repo # Repository name
GITHUB_REPOSITORY_OWNER=owner # Owner username
```

### What We Use

**File:** `scripts/update_manifest.py`

```python
# Get environment variables
workflow_run_number = os.getenv('GITHUB_RUN_NUMBER', 'unknown')  # Display: #42
workflow_run_id = os.getenv('GITHUB_RUN_ID', 'unknown')          # Link: 8234567890
```

### PR Body Generation

**File:** `scripts/update_manifest.py` → `create_pull_request()`

```python
# Build PR body with separate links for repo and workflow run
repo_url = f"https://github.com/{fork_owner}/{repo_name}"
workflow_url = f"https://github.com/{fork_owner}/{repo_name}/actions/runs/{workflow_run_id}"
body = f"Automated by [{fork_owner}/{repo_name}]({repo_url}) in workflow run [#{workflow_run_number}]({workflow_url})."
```

**Notice:**
- Repo name links to repository homepage (for general info)
- Run number links to specific workflow execution (for detailed logs)

### Real Example

When:
- Run number = `42`
- Run ID = `8234567890`

**URL Generated:**
```
https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/8234567890
```

**PR Body:**
```markdown
Automated by [zeldrisho/winget-pkgs-updater](https://github.com/zeldrisho/winget-pkgs-updater) in workflow run [#42](https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/8234567890).
```

**Rendered in GitHub:**
> Automated by [zeldrisho/winget-pkgs-updater](https://github.com/zeldrisho/winget-pkgs-updater) in workflow run [#42](https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/8234567890).

### Why This Matters

1. **Traceability**: Each PR links to the exact workflow run that created it
2. **Transparency**: Reviewers can see logs, verify checksums, check what happened
3. **Debugging**: If something goes wrong, easy to find which run caused it
4. **Accountability**: Clear automation trail

### How to Verify

After workflow runs, you can:

1. Go to **Actions** tab in your repo
2. Click on the workflow run
3. See the run ID in the URL:
   ```
   https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/8234567890
                                                              ^^^^^^^^^^
                                                              This is GITHUB_RUN_ID
   ```
4. That same ID will be in the PR body!

### Run Number vs Run ID

**Run Number** (`GITHUB_RUN_NUMBER`):
- Sequential: 1, 2, 3, 4, ...
- Human readable
- Resets if workflow is deleted/recreated
- Not unique across repos
- ✅ **Used for display: "workflow run #42"**

**Run ID** (`GITHUB_RUN_ID`):
- Unique globally across GitHub
- Never reused
- Permanent identifier
- Long number like 8234567890
- ✅ **Used in URL: `.../actions/runs/8234567890`**

### Why Use Both?

1. **Run Number (#42)** - Easy to read, matches GitHub UI
   - When you see "Update WinGet Packages #42" in Actions tab
   - That's the run number!

2. **Run ID (8234567890)** - Unique URL identifier
   - Needed for the actual link to work
   - Never changes, never conflicts

### Code Flow

```
1. Workflow starts
   ├─ GitHub sets GITHUB_RUN_NUMBER=42
   ├─ GitHub sets GITHUB_RUN_ID=8234567890
   └─ GitHub sets other env vars

2. check_version.py runs
   └─ Detects new version

3. update_manifest.py runs
   ├─ Reads: workflow_run_number = os.getenv('GITHUB_RUN_NUMBER')  → "42"
   ├─ Reads: workflow_run_id = os.getenv('GITHUB_RUN_ID')          → "8234567890"
   ├─ Builds URL: f"...actions/runs/{workflow_run_id}"             → uses 8234567890
   ├─ Builds text: f"workflow run #{workflow_run_number}"          → uses 42
   └─ Creates PR with both combined

4. PR created in microsoft/winget-pkgs
   └─ Body: "...in workflow run [#42](url)" (both links clickable)
```

### Example URLs (Real Format)

**GitHub Actions UI:**
```
https://github.com/zeldrisho/winget-pkgs-updater/actions/runs/8234567890
                                                                ^^^^^^^^^^
                                                                Run ID
```

Shows in UI as: **"Update WinGet Packages #42"** ← Run Number

**In PR body:**
```markdown
in workflow run #42
                 ^^
                 Run Number (human readable)
```

**Click the link → Go to:**
```
https://github.com/.../actions/runs/8234567890
                                   ^^^^^^^^^^
                                   Run ID (unique identifier)
```

---

## Summary

- ✅ **Display:** Uses `GITHUB_RUN_NUMBER` → Shows as `#42`
- ✅ **Link:** Uses `GITHUB_RUN_ID` → Points to run `8234567890`
- ✅ **Best of both:** Human readable + Unique identifier
- ✅ **Matches GitHub UI:** Same as "Update WinGet Packages #42"
- ✅ **Always works:** Links never break, numbers never conflict

**Example result:**
```markdown
Automated by [zeldrisho/winget-pkgs-updater](https://github.com/zeldrisho/winget-pkgs-updater) in workflow run [#42](https://github.com/.../runs/8234567890).
                                                        ↑ Link to repo                                     ↑ Link to run
```
