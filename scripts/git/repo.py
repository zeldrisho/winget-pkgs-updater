"""
Git repository operations (clone, branch, commit, push)
"""

import sys
import subprocess
import json


def clone_winget_pkgs(fork_repo: str, temp_dir: str, token: str) -> bool:
    """Clone forked winget-pkgs repository and sync with upstream"""
    try:
        # Use token in URL for authentication
        repo_url = f"https://{token}@github.com/{fork_repo}.git"
        print(f"Cloning https://github.com/{fork_repo}.git...")
        
        # Clone with more depth to ensure we get recent versions
        subprocess.run(
            ['git', 'clone', '--depth', '50', repo_url, temp_dir],
            check=True,
            capture_output=True
        )
        
        # Add upstream remote and fetch latest
        print(f"Syncing with upstream microsoft/winget-pkgs...")
        subprocess.run(
            ['git', 'remote', 'add', 'upstream', 'https://github.com/microsoft/winget-pkgs.git'],
            cwd=temp_dir,
            check=True,
            capture_output=True
        )
        
        # Fetch upstream master branch (shallow to avoid too much data)
        subprocess.run(
            ['git', 'fetch', 'upstream', 'master', '--depth', '50'],
            cwd=temp_dir,
            check=True,
            capture_output=True
        )
        
        # Merge upstream/master into current branch
        print(f"Merging latest changes from upstream...")
        result = subprocess.run(
            ['git', 'merge', 'upstream/master', '--no-edit', '--strategy-option', 'theirs'],
            cwd=temp_dir,
            capture_output=True
        )
        
        if result.returncode != 0:
            # If merge failed, try reset to upstream/master
            print(f"⚠️  Merge failed, resetting to upstream/master...")
            subprocess.run(
                ['git', 'reset', '--hard', 'upstream/master'],
                cwd=temp_dir,
                check=True,
                capture_output=True
            )
        else:
            print(f"✅ Successfully synced with upstream")
        
        # Git user config is now set globally in the workflow
        # No need to configure it here - it will use the global config
        
        return True
    except Exception as e:
        print(f"Error cloning repository: {e}", file=sys.stderr)
        return False


def create_pr_branch(repo_dir: str, package_id: str, version: str) -> str:
    """
    Create and checkout new branch for PR.
    Returns branch_name.
    Note: Branch existence checking is now done in the workflow.
    """
    branch_name = f"{package_id}-{version}"
    try:
        # Check if branch already exists locally
        result = subprocess.run(
            ['git', 'rev-parse', '--verify', branch_name],
            cwd=repo_dir,
            capture_output=True
        )
        
        if result.returncode == 0:
            # Branch exists locally, delete it
            print(f"⚠️  Branch '{branch_name}' exists locally, deleting...")
            subprocess.run(
                ['git', 'branch', '-D', branch_name],
                cwd=repo_dir,
                check=True,
                capture_output=True
            )
        
        # Create new branch
        subprocess.run(
            ['git', 'checkout', '-b', branch_name],
            cwd=repo_dir,
            check=True,
            capture_output=True
        )
        return branch_name
    except Exception as e:
        print(f"Error creating branch: {e}", file=sys.stderr)
        raise


def commit_and_push(repo_dir: str, package_id: str, version: str, branch_name: str, token: str) -> bool:
    """Commit changes and push to fork"""
    try:
        # Add changes
        subprocess.run(
            ['git', 'add', '.'],
            cwd=repo_dir,
            check=True
        )
        
        # Check if there are changes to commit
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not status_result.stdout.strip():
            print("⚠️  No changes to commit")
            return True  # Not an error, just nothing to do
        
        # Commit
        commit_msg = f"New version: {package_id} version {version}"
        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            cwd=repo_dir,
            check=True
        )
        
        # Get remote URL with token
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            cwd=repo_dir,
            check=True,
            capture_output=True,
            text=True
        )
        remote_url = result.stdout.strip()
        
        # Update remote URL with token if not already present
        if token not in remote_url and not remote_url.startswith('https://'):
            # Assume it's SSH, convert to HTTPS with token
            if remote_url.startswith('git@github.com:'):
                repo_path = remote_url.replace('git@github.com:', '').replace('.git', '')
                remote_url = f"https://{token}@github.com/{repo_path}.git"
                subprocess.run(
                    ['git', 'remote', 'set-url', 'origin', remote_url],
                    cwd=repo_dir,
                    check=True
                )
        
        # Push to remote
        print(f"Pushing to origin/{branch_name}...")
        subprocess.run(
            ['git', 'push', 'origin', branch_name],
            cwd=repo_dir,
            check=True
        )
        print(f"✅ Successfully pushed to origin/{branch_name}")
        
        return True
    except Exception as e:
        print(f"Error committing/pushing: {e}", file=sys.stderr)
        return False


def configure_git_user(repo_dir: str) -> bool:
    """
    Configure git user.name and user.email from GitHub API.
    """
    try:
        print("Configuring git user from GitHub API...")
        # Fetch user info from GitHub CLI
        result = subprocess.run(
            ['gh', 'api', 'user', '--jq', '{login: .login, id: .id, name: .name, email: .email}'],
            capture_output=True,
            text=True,
            check=True
        )
        user_info = json.loads(result.stdout)
        
        login = user_info['login']
        user_id = user_info['id']
        name = user_info['name'] or login
        email = user_info['email']
        
        if not email:
            email = f"{user_id}+{login}@users.noreply.github.com"
            print(f"   Using noreply email: {email}")
        else:
            print(f"   Using GitHub email: {email}")
            
        # Configure git
        subprocess.run(['git', 'config', 'user.name', name], cwd=repo_dir, check=True)
        subprocess.run(['git', 'config', 'user.email', email], cwd=repo_dir, check=True)
        
        return True
    except Exception as e:
        print(f"Error configuring git user: {e}", file=sys.stderr)
        return False
