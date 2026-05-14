import os
import sqlite3
import json
import pickle
import hashlib
import struct
import ctypes
import shutil
import threading
from datetime import datetime, timedelta
from config import BASE_DIR, DB_FILE, AUTH_FILE, REMEMBER_FILE, COL_KEYS

SQLITE_DB  = os.path.join(BASE_DIR, "garment_data.sqlite")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
LOG_DIR    = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

MAX_DAILY_BACKUPS   = 30   # keep last 30 daily backups
MAX_HOURLY_BACKUPS  = 24   # keep last 24 hourly backups

_KEY = b"TasniahFabricsLtd2026MascoGroup!"

def _xor(data: bytes) -> bytes:
    return bytes(b ^ _KEY[i % len(_KEY)] for i, b in enumerate(data))

def _hide_file(filepath):
    if os.path.exists(filepath) and os.name == "nt":
        ctypes.windll.kernel32.SetFileAttributesW(filepath, 0x02)  # HIDDEN only

def _show_file(filepath):
    """Temporarily un-hide a file (needed to overwrite on Windows)."""
    if os.path.exists(filepath) and os.name == "nt":
        ctypes.windll.kernel32.SetFileAttributesW(filepath, 128)

# ── SQLite helpers ─────────────────────────────────────────────────────────────
def _init_sqlite():
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()
    cols_def = ", ".join([f"{k} TEXT" for k in COL_KEYS])
    c.execute(f"CREATE TABLE IF NOT EXISTS orders "
              f"(id INTEGER PRIMARY KEY AUTOINCREMENT, {cols_def})")
    c.execute("CREATE TABLE IF NOT EXISTS app_metadata "
              "(key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    conn.close()

def _migrate_schema():
    """Ensure SQLite table has all columns defined in COL_KEYS."""
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()
    c.execute("PRAGMA table_info(orders)")
    existing = {row[1] for row in c.fetchall()}
    for k in COL_KEYS:
        if k not in existing:
            try:
                c.execute(f"ALTER TABLE orders ADD COLUMN {k} TEXT")
                print(f"Added missing column: {k}")
            except Exception as e:
                print(f"Migration error for {k}: {e}")
    conn.commit()
    conn.close()

def _migrate_old_data_if_exists():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "rb") as f:
                ln  = struct.unpack(">I", f.read(4))[0]
                enc = f.read(ln)
            d = pickle.loads(_xor(enc))
            db_save(d)
            print("Successfully migrated data to SQLite.")
            if os.path.exists(DB_FILE + ".migrated"):
                os.remove(DB_FILE + ".migrated")
            os.rename(DB_FILE, DB_FILE + ".migrated")
        except Exception as e:
            print(f"Migration error: {e}")

# ── Backup Engine ──────────────────────────────────────────────────────────────
def _prune_backups(folder: str, prefix: str, keep: int):
    """Delete old backup files, keeping only the newest `keep` ones."""
    try:
        files = sorted(
            [f for f in os.listdir(folder) if f.startswith(prefix)],
            reverse=True
        )
        for old in files[keep:]:
            try: os.remove(os.path.join(folder, old))
            except: pass
    except: pass


def _do_backup(label: str, subfolder: str, prefix: str, max_keep: int) -> str:
    """
    Perform a single SQLite backup.
    Returns the path of the created backup, or "" if skipped/failed.
    """
    if not os.path.exists(SQLITE_DB):
        return ""
    dest_dir = os.path.join(BACKUP_DIR, subfolder)
    os.makedirs(dest_dir, exist_ok=True)

    stamp      = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dest_path  = os.path.join(dest_dir, f"{prefix}_{stamp}.sqlite")

    try:
        # Use SQLite's online backup API — safe even while DB is open
        src  = sqlite3.connect(SQLITE_DB)
        dst  = sqlite3.connect(dest_path)
        src.backup(dst)
        src.close()
        dst.close()
        _hide_file(dest_path)
        _prune_backups(dest_dir, prefix, max_keep)
        return dest_path
    except Exception as e:
        print(f"[Backup:{label}] Error: {e}")
        return ""


def backup_daily() -> str:
    """One backup per day — called at startup."""
    dest_dir = os.path.join(BACKUP_DIR, "daily")
    os.makedirs(dest_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    # Only create if today's backup doesn't already exist
    if any(f.startswith(f"daily_{today}") for f in os.listdir(dest_dir)):
        return ""   # already done today
    return _do_backup("daily", "daily", "daily", MAX_DAILY_BACKUPS)


def backup_on_close() -> str:
    """Immediate backup when the app is about to close."""
    return _do_backup("on-close", "on_close", "close", MAX_HOURLY_BACKUPS)


def backup_manual() -> str:
    """Manual backup triggered by the user."""
    dest_dir = os.path.join(BACKUP_DIR, "manual")
    os.makedirs(dest_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest_path = os.path.join(dest_dir, f"manual_{stamp}.sqlite")
    try:
        src = sqlite3.connect(SQLITE_DB)
        dst = sqlite3.connect(dest_path)
        src.backup(dst)
        src.close(); dst.close()
        return dest_path
    except Exception as e:
        print(f"[Manual Backup] Error: {e}")
        return ""


def get_backup_info() -> dict:
    """Return counts and latest timestamps for each backup category."""
    info = {}
    for sub in ("daily", "on_close", "manual"):
        d = os.path.join(BACKUP_DIR, sub)
        if not os.path.isdir(d):
            info[sub] = {"count": 0, "latest": "—"}
            continue
        files = sorted(os.listdir(d), reverse=True)
        info[sub] = {
            "count":  len(files),
            "latest": files[0].replace(".sqlite", "").replace("_", " ") if files else "—",
        }
    return info


# ── Scheduled hourly backup (background thread) ────────────────────────────────
_backup_thread: threading.Thread | None = None
_stop_backup   = threading.Event()

def start_scheduled_backup(interval_hours: float = 1.0):
    """Start background thread that backs up every `interval_hours`."""
    global _backup_thread
    _stop_backup.clear()

    def _loop():
        while not _stop_backup.wait(timeout=interval_hours * 3600):
            _do_backup("scheduled", "daily", "daily", MAX_DAILY_BACKUPS)

    _backup_thread = threading.Thread(target=_loop, daemon=True, name="AutoBackup")
    _backup_thread.start()


def stop_scheduled_backup():
    _stop_backup.set()


# ── Legacy shim (called by old code) ──────────────────────────────────────────
def _backup_sqlite():
    backup_daily()


# ── Load / Save ───────────────────────────────────────────────────────────────
def db_load() -> dict:
    needs_migration = not os.path.exists(SQLITE_DB)
    _init_sqlite()
    _migrate_schema()
    if needs_migration:
        _migrate_old_data_if_exists()
    backup_daily()                # startup: one daily backup
    start_scheduled_backup(1.0)   # hourly backup in background

    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(f"SELECT {', '.join(COL_KEYS)} FROM orders")
    orders = [dict(r) for r in c.fetchall()]
    c.execute("SELECT key, value FROM app_metadata")
    meta = {row["key"]: json.loads(row["value"]) for row in c.fetchall()}
    conn.close()

    return {
        "orders":            orders,
        "version":           meta.get("version", 1),
        "country_cutoff":    meta.get("country_cutoff", {}),
        "factory_merchants": meta.get("factory_merchants", []),
    }


def db_save(data: dict):
    _show_file(SQLITE_DB)
    conn = sqlite3.connect(SQLITE_DB)
    c = conn.cursor()
    c.execute("DELETE FROM orders")
    if data.get("orders"):
        placeholders = ", ".join(["?"] * len(COL_KEYS))
        query = (f"INSERT INTO orders ({', '.join(COL_KEYS)}) "
                 f"VALUES ({placeholders})")
        c.executemany(query, [
            tuple(str(o.get(k, "")) for k in COL_KEYS)
            for o in data["orders"]
        ])
    meta_items = [
        ("version",           json.dumps(data.get("version", 1))),
        ("country_cutoff",    json.dumps(data.get("country_cutoff", {}))),
        ("factory_merchants", json.dumps(data.get("factory_merchants", []))),
    ]
    c.executemany("REPLACE INTO app_metadata (key, value) VALUES (?, ?)", meta_items)
    conn.commit()
    conn.close()
    _hide_file(SQLITE_DB)


def log_action(user: str, action: str, details: str):
    """Log an action to the audit log file."""
    log_file = os.path.join(LOG_DIR, f"audit_{datetime.now().strftime('%Y-%m')}.json")
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "action": action,
        "details": details
    }
    try:
        logs = []
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
        logs.append(entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Logging error: {e}")

# ── Auth helpers ───────────────────────────────────────────────────────────────
def _hp(pw):
    return hashlib.sha256((pw + "TasniahSalt2026").encode()).hexdigest()

def auth_load() -> dict:
    if not os.path.exists(AUTH_FILE):
        u = {"admin": {"password": _hp("admin123"), "role": "admin",
                        "name": "Administrator"}}
        _auth_save(u); return u
    try:
        with open(AUTH_FILE, "rb") as f: enc = f.read()
        return pickle.loads(_xor(enc))
    except Exception:
        u = {"admin": {"password": _hp("admin123"), "role": "admin",
                        "name": "Administrator"}}
        _auth_save(u); return u

def _auth_save(users: dict):
    _show_file(AUTH_FILE)          # un-hide before overwrite (Windows)
    with open(AUTH_FILE, "wb") as f:
        f.write(_xor(pickle.dumps(users)))
    _hide_file(AUTH_FILE)

def auth_verify(u, p, users):
    rec = users.get(u.lower())
    return rec if rec and rec["password"] == _hp(p) else None

def load_remembered():
    if not os.path.exists(REMEMBER_FILE): return ("", "")
    try:
        with open(REMEMBER_FILE, "rb") as f: enc = f.read()
        d = pickle.loads(_xor(enc))
        return d.get("u", ""), d.get("p", "")
    except: return ("", "")

def save_remembered(u, p):
    if os.path.exists(REMEMBER_FILE) and os.name == "nt":
        ctypes.windll.kernel32.SetFileAttributesW(REMEMBER_FILE, 128)
    try:
        with open(REMEMBER_FILE, "wb") as f:
            f.write(_xor(pickle.dumps({"u": u, "p": p})))
        _hide_file(REMEMBER_FILE)
    except: pass

def clear_remembered():
    save_remembered("", "")
def get_logs():
    """Read all log entries from the logs directory."""
    import json
    all_logs = []
    if not os.path.exists(LOG_DIR): return []
    try:
        files = [f for f in os.listdir(LOG_DIR) if f.endswith(".json")]
        for f in sorted(files, reverse=True):
            with open(os.path.join(LOG_DIR, f), "r", encoding="utf-8") as file:
                all_logs.extend(json.load(file))
        # Sort by timestamp descending
        return sorted(all_logs, key=lambda x: x.get("timestamp", ""), reverse=True)
    except:
        return []
