import subprocess
import os
import re
from config import VERSION, BASE_DIR

def check_for_updates():
    """
    Checks GitHub for a newer version using git commands.
    This supports private repositories if the local git is authenticated.
    Returns (True, remote_version) if update available, (False, None) otherwise.
    """
    try:
        # 1. Ensure it's a git repo
        if not os.path.exists(os.path.join(BASE_DIR, ".git")):
            return False, None

        # 2. Fetch latest info from remote
        subprocess.run(["git", "fetch"], cwd=BASE_DIR, capture_output=True, check=True)

        # 3. Check if we are behind
        # count how many commits origin/main is ahead of HEAD
        # Note: assuming branch is 'main'. Could use 'git rev-parse --abbrev-ref HEAD' to be dynamic.
        branch_res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], 
                                     cwd=BASE_DIR, capture_output=True, text=True, check=True)
        branch = branch_res.stdout.strip()
        
        res = subprocess.run(["git", "rev-list", "--count", f"HEAD..origin/{branch}"], 
                             cwd=BASE_DIR, capture_output=True, text=True, check=True)
        
        count = int(res.stdout.strip())
        if count > 0:
            # 4. Get the version from the remote config.py
            show_res = subprocess.run(["git", "show", f"origin/{branch}:config.py"], 
                                       cwd=BASE_DIR, capture_output=True, text=True, check=True)
            content = show_res.stdout
            match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', content)
            if match:
                remote_version = match.group(1)
                
                # 5. Get the remote changelog.json
                try:
                    cl_res = subprocess.run(["git", "show", f"origin/{branch}:changelog.json"], 
                                            cwd=BASE_DIR, capture_output=True, text=True, check=True)
                    import json
                    remote_changelog = json.loads(cl_res.stdout)
                except:
                    remote_changelog = []

                if remote_version != VERSION:
                    return True, remote_version, remote_changelog
    except Exception as e:
        print(f"Update check failed: {e}")
    
    return False, None, None

def perform_git_update():
    """
    Attempts to update the application using git pull.
    Returns (success, message).
    """
    try:
        if not os.path.exists(os.path.join(BASE_DIR, ".git")):
            return False, "This is not a Git repository. Please clone from GitHub to enable auto-updates."
        
        result = subprocess.run(["git", "pull"], cwd=BASE_DIR, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Git pull failed: {e.stderr}"
    except Exception as e:
        return False, f"Update error: {str(e)}"
