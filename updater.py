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
    """Generates a unique hardware ID for the current PC."""
    import uuid as _uuid
    try:
        # Guaranteed unique ID based on the machine's MAC address
        node = _uuid.getnode()
        hwid = hashlib.sha256(str(node).encode()).hexdigest()[:16].upper()
        return f"GT-{hwid}"
    except Exception:
        return "GT-DEFAULT-UUID"

def _get_github_content(path):
    """গিটহাব এপিআই ব্যবহার করে পাবলিক রিপোজিটরি থেকে ফাইলের ডাটা সংগ্রহ করে।"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {
        "Accept": "application/vnd.github.v3.raw"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')

def validate_license(license_key):
    """লাইসেন্স কি যাচাই করার আর প্রয়োজন নেই, সরাসরি ট্রু রিটার্ন করবে।"""
    return True, "লাইসেন্স সিস্টেম নিষ্ক্রিয় করা হয়েছে।"

def check_for_updates(license_key=None):
    """নতুন আপডেট চেক করে। লাইসেন্স চেকিং বাদ দেওয়া হয়েছে।"""
    try:
        # ১. নতুন ভার্সন চেক
        config_content = _get_github_content("config.py")
        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', config_content)
        if match:
            remote_version = match.group(1)
            
            # ২. চ্যাঞ্জলগ সংগ্রহ
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
    """গিটহাব থেকে সরাসরি জিপ ফাইল ডাউনলোড করে অ্যাপ আপডেট করে।"""
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/zipball/main"
        req = urllib.request.Request(url)
        
        with urllib.request.urlopen(req) as response:
            with zipfile.ZipFile(io.BytesIO(response.read())) as zip_ref:
                temp_dir = os.path.join(BASE_DIR, "update_temp")
                if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
                os.makedirs(temp_dir)
                zip_ref.extractall(temp_dir)
                
                root_folder = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                
                # গুরুত্বপূর্ণ ফাইলগুলো বাদ দিয়ে বাকি সব আপডেট করা
                skip_files = ["garment_data.sqlite", "garment_data.dat", "app_settings.json", "auth.dat", "remember.dat"]
                skip_dirs  = ["backups", "logs", "__pycache__", ".git"]

                for item in os.listdir(root_folder):
                    s = os.path.join(root_folder, item)
                    d = os.path.join(BASE_DIR, item)
                    
                    if item in skip_files or item in skip_dirs: continue
                        
                    if os.path.isdir(s):
                        if os.path.exists(d): shutil.rmtree(d)
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)
                
                shutil.rmtree(temp_dir)
                return True, "সিস্টেম সফলভাবে আপডেট হয়েছে। দয়া করে অ্যাপটি রিস্টার্ট করুন।"
    except Exception as e:
        return False, f"আপডেট ব্যর্থ হয়েছে: {str(e)}"
