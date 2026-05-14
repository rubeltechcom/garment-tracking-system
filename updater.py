import urllib.request
import json
import zipfile
import os
import io
import re
import shutil
import subprocess
import hashlib
from config import VERSION, BASE_DIR, GITHUB_TOKEN, REPO_OWNER, REPO_NAME

def get_hwid():
    """Generates a unique hardware ID for the current PC using Windows UUID."""
    try:
        # Use wmic to get the machine's UUID
        cmd = 'wmic csproduct get uuid'
        uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        # Hash it for professional look and security
        return hashlib.sha256(uuid.encode()).hexdigest()[:16].upper()
    except Exception:
        # Fallback if wmic fails
        return "DEV-UNKNOWN-000"

def _get_github_content(path):
    """Fetches raw content of a file from the private GitHub repository."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')

def validate_license(license_key):
    """
    Validates the local license key and device HWID against the remote licenses.json.
    Returns (True, "Message") or (False, "Error Message").
    """
    if not license_key or license_key == "NONE":
        return False, "No license key entered. Please check settings."
    
    try:
        content = _get_github_content("licenses.json")
        licenses_data = json.loads(content)
        
        current_hwid = get_hwid()
        
        # Check if license exists and matches the HWID
        if license_key in licenses_data:
            authorized_hwid = licenses_data[license_key]
            if authorized_hwid == current_hwid:
                return True, "License validated."
            else:
                return False, f"License key '{license_key}' is already bound to another device."
        else:
            return False, f"Invalid license key: '{license_key}'. Contact administrator."
            
    except Exception as e:
        return False, f"License validation error: {str(e)}"

def check_for_updates(license_key):
    """
    Checks for updates. First validates the license, then checks version and changelog.
    Returns (True, remote_version, remote_changelog) if update available.
    """
    # 1. Validate License First
    valid, msg = validate_license(license_key)
    if not valid:
        return False, None, f"LICENSE_ERROR: {msg}"

    try:
        # 2. Check Remote Version
        config_content = _get_github_content("config.py")
        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', config_content)
        if match:
            remote_version = match.group(1)
            
            # 3. Fetch Remote Changelog
            try:
                cl_content = _get_github_content("changelog.json")
                remote_changelog = json.loads(cl_content)
            except:
                remote_changelog = []
                
            if remote_version != VERSION:
                return True, remote_version, remote_changelog
    except Exception as e:
        print(f"Update check failed: {e}")
    
    return False, None, None

def perform_git_update():
    """
    Performs a full update by downloading the latest ZIP archive from GitHub
    and extracting it over the current installation.
    """
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/zipball/main"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            with zipfile.ZipFile(io.BytesIO(response.read())) as zip_ref:
                # 1. Create a temp folder for extraction
                temp_dir = os.path.join(BASE_DIR, "update_temp")
                if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
                os.makedirs(temp_dir)
                
                zip_ref.extractall(temp_dir)
                
                # 2. Identify the root folder inside the ZIP (GitHub creates a named root)
                root_folder = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                
                # 3. Overwrite local files (excluding database and settings if desired)
                # For this system, we'll overwrite everything EXCEPT .sqlite, .dat, .json (settings)
                # and backups folder.
                skip_files = ["garment_data.sqlite", "garment_data.dat", "app_settings.json", "auth.dat", "remember.dat"]
                skip_dirs  = ["backups", "logs", "__pycache__", ".git"]

                for item in os.listdir(root_folder):
                    s = os.path.join(root_folder, item)
                    d = os.path.join(BASE_DIR, item)
                    
                    if item in skip_files or item in skip_dirs:
                        continue
                        
                    if os.path.isdir(s):
                        if os.path.exists(d): shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                
                # 4. Cleanup
                shutil.rmtree(temp_dir)
                return True, "Application updated successfully. Please restart."
    except Exception as e:
        return False, f"Update failed: {str(e)}"
