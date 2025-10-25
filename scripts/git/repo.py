"""
Git repository operations (clone, branch, commit, push)
"""

import sys
import subprocess


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
        
        # Configure git
        subprocess.run(
            ['git', 'config', 'user.name', 'github-actions[bot]'],
            cwd=temp_dir,
            check=True
        )
        subprocess.run(
            ['git', 'config', 'user.email', 'github-actions[bot]@users.noreply.github.com'],
            cwd=temp_dir,
            check=True
        )
        
        return True
    except Exception as e:
        print(f"Error cloning repository: {e}", file=sys.stderr)
        return False


def create_pr_branch(repo_dir: str, package_id: str, version: str) -> str:
    """Create and checkout new branch for PR"""
    branch_name = f"{package_id}-{version}"
    try:
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
        
        # Push
        subprocess.run(
            ['git', 'push', 'origin', branch_name],
            cwd=repo_dir,
            check=True
        )
        
        return True
    except Exception as e:
        print(f"Error committing/pushing: {e}", file=sys.stderr)
        return False
