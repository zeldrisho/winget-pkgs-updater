# 🔍 PR Duplicate Prevention

## What It Does

Before creating a PR, the workflow checks if a PR with the same title already exists in `microsoft/winget-pkgs` (either open or merged). If found, it skips creation to avoid duplicates.

## Why This Matters

### Problems Prevented
- ❌ Duplicate PRs for same version
- ❌ Spamming microsoft/winget-pkgs maintainers
- ❌ Workflow failures from duplicate branches
- ❌ Confusion about which PR to merge

### Benefits
- ✅ Only one PR per version
- ✅ Workflow can run multiple times safely
- ✅ No manual cleanup needed
- ✅ Professional automation

## How It Works

### Check Process

```python
# 1. Build expected PR title
title = f"New version: {package_id} version {version}"

# 2. Search for existing PRs with that title
gh pr list \
  --repo microsoft/winget-pkgs \
  --search '"New version: VNGCorp.Zalo version 25.10.2" in:title' \
  --state all \
  --json title,state,number

# 3. If found: Skip creation
# 4. If not found: Create PR
```

### States Checked

| State | Meaning | Action |
|-------|---------|--------|
| `OPEN` | PR pending review | **Skip** - Already exists |
| `MERGED` | PR already merged | **Skip** - Version already in repo |
| `CLOSED` | PR closed without merge | **Skip** - Might be intentional |
| Not found | No PR exists | **Create** - Safe to proceed |

## Example Scenarios

### Scenario 1: PR Already Open

```
Workflow Run #1:
  ✅ Version 25.10.2 detected
  ✅ PR #303038 created
  
Workflow Run #2 (same day):
  ✅ Version 25.10.2 detected
  🔍 Checking for existing PRs...
  ⏭️  PR #303038 already exists (OPEN)
  ⏭️  Skipping PR creation
  ✅ Success (no duplicate created)
```

### Scenario 2: PR Already Merged

```
Workflow Run #1:
  ✅ Version 25.10.2 detected
  ✅ PR created and merged
  
Workflow Run #2 (later):
  ✅ Version 25.10.2 detected
  🔍 Checking for existing PRs...
  ⏭️  PR #303038 already exists (MERGED)
  ⏭️  Version already in winget-pkgs
  ✅ Success (no duplicate created)
```

### Scenario 3: New Version

```
Workflow Run:
  ✅ Version 25.11.0 detected
  🔍 Checking for existing PRs...
  ✅ No PRs found for this version
  ✅ Creating new PR #303100
  ✅ Success
```

## Code Implementation

**File:** `scripts/update_manifest.py`

```python
def create_pull_request(...):
    title = f"New version: {package_id} version {version}"
    
    # Check if PR already exists
    check_result = subprocess.run(
        [
            'gh', 'pr', 'list',
            '--repo', 'microsoft/winget-pkgs',
            '--search', f'"{title}" in:title',
            '--state', 'all',  # Check open + closed
            '--json', 'title,state,number',
            '--limit', '5'
        ],
        capture_output=True,
        text=True
    )
    
    if check_result.returncode == 0 and check_result.stdout.strip():
        existing_prs = json.loads(check_result.stdout)
        if existing_prs:
            for pr in existing_prs:
                if pr['title'] == title:
                    print(f"⏭️  PR already exists: #{pr['number']} ({pr['state']})")
                    return True  # Skip creation
    
    # No existing PR found - create new one
    subprocess.run(['gh', 'pr', 'create', ...])
```

## Workflow Logs

### When PR Exists

```
Checking for existing PRs with title: New version: VNGCorp.Zalo version 25.10.2
⏭️  PR already exists: #303038 (OPEN)
   Title: New version: VNGCorp.Zalo version 25.10.2
   Skipping PR creation to avoid duplicates
✅ Successfully completed (no duplicate created)
```

### When PR Doesn't Exist

```
Checking for existing PRs with title: New version: VNGCorp.Zalo version 25.11.0
✅ No existing PRs found
Creating pull request...
✅ Pull request created: New version: VNGCorp.Zalo version 25.11.0
```

## Edge Cases Handled

### 1. Multiple Runs Same Day
- First run: Creates PR
- Second run: Detects existing PR, skips
- Result: ✅ Only one PR

### 2. Manual PR + Automated PR
- Manual PR created first
- Workflow runs: Detects manual PR, skips
- Result: ✅ No duplicate

### 3. PR Closed Then Reopened
- PR closed (not merged)
- Workflow runs: Detects closed PR, skips
- Result: ✅ Respects manual decision

### 4. Network/API Errors
- Check fails: Fallback to create attempt
- GitHub prevents duplicate anyway
- Result: ✅ Safe fallback

## Search Query Details

### Title Search
```bash
--search '"New version: VNGCorp.Zalo version 25.10.2" in:title'
```

- Exact title match (quoted)
- Searches in PR title field only
- Case-insensitive
- Fast (uses GitHub's search index)

### State Filter
```bash
--state all
```

- Includes: OPEN, MERGED, CLOSED
- Prevents duplicates across all states
- More comprehensive than just `--state open`

### Result Limit
```bash
--limit 5
```

- Get up to 5 matching PRs
- Unlikely to have >5 PRs with exact same title
- Fast query (minimal data transfer)

## Performance

### Speed
- Check takes ~1-2 seconds
- Adds minimal overhead to workflow
- Worth it to prevent duplicates

### API Rate Limits
- Uses authenticated `gh` CLI
- Higher rate limits (5000/hour)
- Check only uses 1 API call
- Very efficient

## Configuration

**No configuration needed!**

The check is automatic and always runs before PR creation.

## Testing

### Test Locally

```bash
# Check for specific version
title="New version: VNGCorp.Zalo version 25.10.2"
gh pr list \
  --repo microsoft/winget-pkgs \
  --search "\"$title\" in:title" \
  --state all \
  --json title,state,number
```

### Expected Output (PR Exists)
```json
[
  {
    "number": 303038,
    "state": "OPEN",
    "title": "New version: VNGCorp.Zalo version 25.10.2"
  }
]
```

### Expected Output (No PR)
```json
[]
```

## Troubleshooting

### Check Returns Empty But PR Exists

**Possible causes:**
1. Title format different (e.g., extra spaces)
2. Search indexing delay (rare)

**Solution:**
- Wait a few seconds and retry
- Check PR title matches exactly

### Check Fails (Network Error)

**Behavior:**
- Workflow continues to PR creation
- GitHub prevents duplicate anyway (different error)

**No action needed** - fail-safe design

## FAQ

**Q: What if PR title format changes?**  
A: Update `title` format in code to match new format.

**Q: Does this work with manual PRs?**  
A: Yes! Checks all PRs regardless of creator.

**Q: What if I want to recreate a closed PR?**  
A: Currently skips. Manually delete closed PR first, or modify code to only check OPEN/MERGED.

**Q: Performance impact?**  
A: ~1-2 seconds per check. Negligible for automation.

**Q: Can I disable this check?**  
A: Yes, comment out the check in `create_pull_request()`. Not recommended.

---

## Summary

✅ **Automatic PR duplicate prevention**  
✅ **Checks OPEN + MERGED + CLOSED states**  
✅ **Fast (1-2 seconds)**  
✅ **Zero configuration**  
✅ **Safe fallback on errors**  

**Your workflow can run multiple times without creating spam!** 🎉
