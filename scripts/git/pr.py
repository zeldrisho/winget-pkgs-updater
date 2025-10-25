"""
Pull Request management and checking
"""

import json
import subprocess
import sys


def check_existing_pr(package_id: str, version: str) -> bool:
    """
    Check if PR already exists for this package version.
    Returns True if OPEN or MERGED PR exists (should skip), False otherwise (should create).
    Note: CLOSED PRs are ignored - we can retry them.
    
    Supports both PR title formats:
    - "New version: {package_id} version {version}"
    - "Update {package_id} to {version}"
    """
    try:
        # Search for PRs that contain both package ID and version
        # This catches both "New version: X version Y" and "Update X to Y" formats
        search_query = f"{package_id} {version} in:title"
        print(f"🔍 Checking for existing PRs: {package_id} version {version}")
        
        result = subprocess.run(
            [
                'gh', 'pr', 'list',
                '--repo', 'microsoft/winget-pkgs',
                '--search', search_query,
                '--state', 'all',  # Check open, merged, and closed PRs
                '--json', 'number,title,state',
                '--limit', '10'
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout.strip():
            prs = json.loads(result.stdout)
            if prs:
                for pr in prs:
                    # Check if title contains both package ID and version
                    title_lower = pr['title'].lower()
                    if package_id.lower() in title_lower and version in pr['title']:
                        state = pr['state']
                        state_emoji = "🟢" if state == "OPEN" else "🟣" if state == "MERGED" else "⚪"
                        
                        # Only skip for OPEN or MERGED PRs
                        if state in ["OPEN", "MERGED"]:
                            print(f"⏭️  {state_emoji} PR already exists: #{pr['number']} ({state})")
                            print(f"   Title: {pr['title']}")
                            print(f"   URL: https://github.com/microsoft/winget-pkgs/pull/{pr['number']}")
                            print(f"   Skipping - PR is {state}")
                            return True  # Skip - PR exists and is open/merged
                        else:
                            # CLOSED PR - we can retry
                            print(f"   ⚪ Found CLOSED PR: #{pr['number']}")
                            print(f"   URL: https://github.com/microsoft/winget-pkgs/pull/{pr['number']}")
                            print(f"   Will create new PR (closed PRs can be retried)")
        
        print("✅ No active PR found - will create new one")
        return False  # No active PR found - should create
        
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not check existing PRs: {e}")
        print("Continuing anyway...")
        return False  # Continue on error


def create_pull_request(
    fork_owner: str,
    package_id: str,
    version: str,
    branch_name: str,
    workflow_run_number: str,
    workflow_run_id: str,
    repo_name: str = "winget-pkgs-updater"
) -> bool:
    """Create pull request using GitHub CLI"""
    try:
        title = f"New version: {package_id} version {version}"
        print(f"Creating PR: {title}")
        
        # Build PR body with separate links for repo and workflow run
        repo_url = f"https://github.com/{fork_owner}/{repo_name}"
        workflow_url = f"https://github.com/{fork_owner}/{repo_name}/actions/runs/{workflow_run_id}"
        body = f"Automated by [{fork_owner}/{repo_name}]({repo_url}) in workflow run [#{workflow_run_number}]({workflow_url})."
        
        # Use gh CLI to create PR
        subprocess.run(
            [
                'gh', 'pr', 'create',
                '--repo', 'microsoft/winget-pkgs',
                '--title', title,
                '--body', body,
                '--head', f"{fork_owner}:{branch_name}"
            ],
            check=True
        )
        
        print(f"✅ Pull request created: {title}")
        print(f"📝 Workflow run: {workflow_url}")
        return True
        
    except Exception as e:
        print(f"Error creating PR: {e}", file=sys.stderr)
        return False
