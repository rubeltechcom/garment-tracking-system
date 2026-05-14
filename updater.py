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
    """পিসির জন্য একটি ইউনিক হার্ডওয়্যার আইডি (HWID) জেনারেট করে।"""
    try:
        # Windows UUID সংগ্রহ করা
        cmd = 'wmic csproduct get uuid'
        uuid = subprocess.check_output(cmd, shell=True).decode().split('\n')[1].strip()
        # সিকিউরিটির জন্য এটিকে হ্যাশ (Hash) করা
        return hashlib.sha256(uuid.encode()).hexdigest()[:16].upper()
    except Exception:
        return "DEV-UNKNOWN-000"

def _get_github_content(path):
    """গিটহাব এপিআই ব্যবহার করে প্রাইভেট রিপোজিটরি থেকে ফাইলের ডাটা সংগ্রহ করে।"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3.raw"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')

def validate_license(license_key):
    """লাইসেন্স কি এবং পিসি আইডি গিটহাবের licenses.json এর সাথে যাচাই করে।"""
    if not license_key or license_key == "NONE":
        return False, "কোনো লাইসেন্স কি পাওয়া যায়নি। সেটিংস চেক করুন।"
    
    try:
        content = _get_github_content("licenses.json")
        licenses_data = json.loads(content)
        current_hwid = get_hwid()
        
        if license_key in licenses_data:
            authorized_hwid = licenses_data[license_key]
            if authorized_hwid == current_hwid:
                return True, "লাইসেন্স সফলভাবে যাচাই করা হয়েছে।"
            else:
                return False, f"এই লাইসেন্স কি-টি অন্য একটি ডিভাইসে নিবন্ধিত।"
        else:
            return False, f"ভুল লাইসেন্স কি! সঠিক কি-এর জন্য অ্যাডমিনের সাথে যোগাযোগ করুন।"
    except Exception as e:
        return False, f"ভ্যালিডেশন ত্রুটি: {str(e)}"

def check_for_updates(license_key):
    """নতুন আপডেট এবং লাইসেন্স চেক করে।"""
    # ১. প্রথমে লাইসেন্স যাচাই
    valid, msg = validate_license(license_key)
    if not valid:
        return False, None, f"LICENSE_ERROR: {msg}"

    try:
        # ২. নতুন ভার্সন চেক
        config_content = _get_github_content("config.py")
        match = re.search(r'VERSION\s*=\s*["\']([^"\']+)["\']', config_content)
        if match:
            remote_version = match.group(1)
            
            # ৩. চ্যাঞ্জলগ সংগ্রহ
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
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            with zipfile.ZipFile(io.BytesIO(response.read())) as zip_ref:
                temp_dir = os.path.join(BASE_DIR, "update_temp")
                if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
                os.makedirs(temp_dir)
                zip_ref.extractall(temp_dir)
                
                root_folder = os.path.join(temp_dir, os.listdir(temp_dir)[0])
                
                # গুরুত্বপূর্ণ ফাইলগুলো বাদ দিয়ে বাকি সব আপডেট করা
                skip_files = ["garment_data.sqlite", "garment_data.dat", "app_settings.json", "auth.dat", "remember.dat", "licenses.json"]
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
