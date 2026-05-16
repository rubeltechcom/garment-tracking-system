import urllib.request
import json
import zipfile
import os
import io
import re
import shutil
import hashlib
from config import VERSION, BASE_DIR, REPO_OWNER, REPO_NAME

def get_hwid() -> str:
    """Generate a unique hardware ID for this machine."""
    import uuid as _uuid
    try:
        node = _uuid.getnode()
        hwid = hashlib.sha256(str(node).encode()).hexdigest()[:16].upper()
        return f"GT-{hwid}"
    except Exception:
        return "GT-DEFAULT-UUID"

def _get_github_content(path: str) -> str:
    """Fetch raw file content from the public GitHub repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github.v3.raw"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode("utf-8")

def validate_license(license_key=None):
    """License validation is disabled — always returns True."""
    return True, "License system inactive."

def check_for_updates(license_key=None):
    """Check GitHub for a newer version. Returns (has_update, version, changelog)."""
    try:
        config_content = _get_github_content("config.py")
        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', config_content)
        if match:
            remote_version = match.group(1)
            try:
                cl_content = _get_github_content("changelog.json")
                remote_changelog = json.loads(cl_content)
            except Exception as e:
                print(f"[Updater] Could not fetch changelog: {e}")
                remote_changelog = []

            if remote_version != VERSION:
                return True, remote_version, remote_changelog
    except Exception as e:
        print(f"[Updater] Update check failed: {e}")

    return False, None, None

def _fetch_release_sha256() -> str | None:
    """
    Try to fetch the expected SHA-256 of the release zip from the repo.
    Returns None if the file is not present (update proceeds without check).
    """
    try:
        content = _get_github_content("release_sha256.txt")
        return content.strip()
    except Exception:
        return None

def perform_git_update():
    """
    Download the latest release zip from GitHub, verify its integrity,
    and copy new files into place — skipping user data files.
    Files are staged to a temp folder first; the swap only happens after
    a successful download and (optional) checksum match.
    """
    temp_dir = os.path.join(BASE_DIR, "update_temp")
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/zipball/main"
        req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=60) as response:
            zip_bytes = response.read()

        # Integrity check: compare SHA-256 if the repo publishes one
        expected_sha = _fetch_release_sha256()
        if expected_sha:
            actual_sha = hashlib.sha256(zip_bytes).hexdigest()
            if actual_sha != expected_sha:
                return False, (
                    f"Download integrity check failed.\n"
                    f"Expected: {expected_sha}\n"
                    f"Got:      {actual_sha}\n"
                    "Update aborted for safety."
                )

        # Extract to staging directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zip_ref:
            zip_ref.extractall(temp_dir)

        root_folder = os.path.join(temp_dir, os.listdir(temp_dir)[0])

        # Files and folders that must never be overwritten during an update
        skip_files = [
            "garment_data.sqlite", "garment_data.dat",
            "app_settings.json", "auth.dat", "auth.json",
            "remember.dat", "remember.json",
        ]
        skip_dirs = ["backups", "logs", "__pycache__", ".git"]

        for item in os.listdir(root_folder):
            if item in skip_files or item in skip_dirs:
                continue
            src = os.path.join(root_folder, item)
            dst = os.path.join(BASE_DIR, item)
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

        shutil.rmtree(temp_dir)
        return True, "Update successful. Please restart the application to apply changes."

    except Exception as e:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
        return False, f"Update failed: {str(e)}"
