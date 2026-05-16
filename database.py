import os
import sqlite3
import json
import hashlib
import ctypes
import shutil
import threading
import secrets as _secrets
from datetime import datetime, timedelta
from config import BASE_DIR, DB_FILE, AUTH_FILE, REMEMBER_FILE, COL_KEYS

SQLITE_DB  = os.path.join(BASE_DIR, "garment_data.sqlite")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")
LOG_DIR    = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

MAX_DAILY_BACKUPS   = 30
MAX_HOURLY_BACKUPS  = 10   # keep last 10 on-close (was 24, too many per day)

# ── File visibility helpers (Windows only) ─────────────────────────────────────
def _hide_file(filepath):
    if os.path.exists(filepath) and os.name == "nt":
        ctypes.windll.kernel32.SetFileAttributesW(filepath, 0x02)

def _show_file(filepath):
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
    # Indexes on commonly filtered/sorted columns
    c.execute("CREATE INDEX IF NOT EXISTS idx_order_no ON orders(order_no)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_country ON orders(country)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_season ON orders(season)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_status ON orders(shipped_status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tod ON orders(tod)")
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
                print(f"[DB] Added missing column: {k}")
            except Exception as e:
                print(f"[DB] Migration error for {k}: {e}")
    conn.commit()
    conn.close()

def _migrate_old_data_if_exists():
    """Migrate legacy pickle-based data file to SQLite."""
    if not os.path.exists(DB_FILE):
        return
    try:
        import pickle, struct
        _KEY = b"TasniahFabricsLtd2026MascoGroup!"
        def _xor(data):
            return bytes(b ^ _KEY[i % len(_KEY)] for i, b in enumerate(data))
        with open(DB_FILE, "rb") as f:
            ln  = struct.unpack(">I", f.read(4))[0]
            enc = f.read(ln)
        d = pickle.loads(_xor(enc))
        db_save(d)
        print("[DB] Successfully migrated legacy data to SQLite.")
        if os.path.exists(DB_FILE + ".migrated"):
            os.remove(DB_FILE + ".migrated")
        os.rename(DB_FILE, DB_FILE + ".migrated")
    except Exception as e:
        print(f"[DB] Legacy migration error: {e}")

# ── Backup Engine ──────────────────────────────────────────────────────────────
def _prune_backups(folder: str, prefix: str, keep: int):
    try:
        files = sorted(
            [f for f in os.listdir(folder) if f.startswith(prefix)],
            reverse=True
        )
        for old in files[keep:]:
            try:
                os.remove(os.path.join(folder, old))
            except Exception as e:
                print(f"[Backup] Could not remove old backup {old}: {e}")
    except Exception as e:
        print(f"[Backup] Prune error in {folder}: {e}")

def _do_backup(label: str, subfolder: str, prefix: str, max_keep: int) -> str:
    if not os.path.exists(SQLITE_DB):
        return ""
    dest_dir = os.path.join(BACKUP_DIR, subfolder)
    os.makedirs(dest_dir, exist_ok=True)
    stamp     = datetime.now().strftime("%Y-%m-%d_%H-%M")
    dest_path = os.path.join(dest_dir, f"{prefix}_{stamp}.sqlite")
    try:
        src = sqlite3.connect(SQLITE_DB)
        dst = sqlite3.connect(dest_path)
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
    dest_dir = os.path.join(BACKUP_DIR, "daily")
    os.makedirs(dest_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    if any(f.startswith(f"daily_{today}") for f in os.listdir(dest_dir)):
        return ""
    return _do_backup("daily", "daily", "daily", MAX_DAILY_BACKUPS)

def backup_on_close() -> str:
    return _do_backup("on-close", "on_close", "close", MAX_HOURLY_BACKUPS)

def backup_manual() -> str:
    dest_dir = os.path.join(BACKUP_DIR, "manual")
    os.makedirs(dest_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest_path = os.path.join(dest_dir, f"manual_{stamp}.sqlite")
    try:
        src = sqlite3.connect(SQLITE_DB)
        dst = sqlite3.connect(dest_path)
        src.backup(dst)
        src.close()
        dst.close()
        return dest_path
    except Exception as e:
        print(f"[Manual Backup] Error: {e}")
        return ""

def get_backup_info() -> dict:
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
    global _backup_thread
    _stop_backup.clear()
    def _loop():
        while not _stop_backup.wait(timeout=interval_hours * 3600):
            _do_backup("scheduled", "daily", "daily", MAX_DAILY_BACKUPS)
    _backup_thread = threading.Thread(target=_loop, daemon=True, name="AutoBackup")
    _backup_thread.start()

def stop_scheduled_backup():
    _stop_backup.set()

# Legacy shim
def _backup_sqlite():
    backup_daily()

# ── Load / Save ────────────────────────────────────────────────────────────────
def db_load() -> dict:
    needs_migration = not os.path.exists(SQLITE_DB)
    _init_sqlite()
    _migrate_schema()
    if needs_migration:
        _migrate_old_data_if_exists()
    backup_daily()
    start_scheduled_backup(1.0)

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
    """
    Save all orders and metadata in a single atomic transaction.
    A crash mid-save will roll back automatically — no partial state.
    """
    _show_file(SQLITE_DB)
    conn = sqlite3.connect(SQLITE_DB)
    try:
        with conn:  # auto-commits on success, rolls back on any exception
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
    finally:
        conn.close()
    _hide_file(SQLITE_DB)

def log_action(user: str, action: str, details: str):
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
        print(f"[Audit] Logging error: {e}")

# ── Auth helpers ───────────────────────────────────────────────────────────────
# Passwords stored as salted SHA-256 hashes in plain JSON — no pickle, no XOR.

_SALT = "TasniahSalt2026"

def _hp(pw: str) -> str:
    return hashlib.sha256((pw + _SALT).encode()).hexdigest()

def auth_load() -> dict:
    """Load user records from JSON. Creates default admin on first run."""
    if not os.path.exists(AUTH_FILE):
        default = {"admin": {"password": _hp("admin123"), "role": "admin",
                              "name": "Administrator", "must_change_password": True}}
        _auth_save(default)
        return default
    try:
        _show_file(AUTH_FILE)
        with open(AUTH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Auth] Failed to load auth file, recreating defaults: {e}")
        default = {"admin": {"password": _hp("admin123"), "role": "admin",
                              "name": "Administrator", "must_change_password": True}}
        _auth_save(default)
        return default

def _auth_save(users: dict):
    """Persist user records as plain JSON (passwords are hashed, never plaintext)."""
    _show_file(AUTH_FILE)
    with open(AUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    _hide_file(AUTH_FILE)

def auth_verify(u: str, p: str, users: dict):
    rec = users.get(u.lower())
    return rec if rec and rec["password"] == _hp(p) else None

# ── Remember-me: stores a session token, never the raw password ────────────────
def generate_session_token() -> str:
    return _secrets.token_hex(32)

def load_remembered() -> tuple[str, str]:
    """Returns (username, session_token) or ("", "")."""
    if not os.path.exists(REMEMBER_FILE):
        return ("", "")
    try:
        _show_file(REMEMBER_FILE)
        with open(REMEMBER_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("u", ""), d.get("token", "")
    except Exception as e:
        print(f"[Auth] Could not load remember-me file: {e}")
        return ("", "")

def save_remembered(u: str, token: str):
    """Persist username + session token (never the raw password)."""
    _show_file(REMEMBER_FILE)
    try:
        with open(REMEMBER_FILE, "w", encoding="utf-8") as f:
            json.dump({"u": u, "token": token}, f)
        _hide_file(REMEMBER_FILE)
    except Exception as e:
        print(f"[Auth] Could not save remember-me file: {e}")

def clear_remembered():
    try:
        if os.path.exists(REMEMBER_FILE):
            _show_file(REMEMBER_FILE)
            os.remove(REMEMBER_FILE)
    except Exception as e:
        print(f"[Auth] Could not clear remember-me file: {e}")

def get_logs() -> list:
    """Read all log entries from the logs directory, newest first."""
    all_logs = []
    if not os.path.exists(LOG_DIR):
        return []
    try:
        files = [f for f in os.listdir(LOG_DIR) if f.endswith(".json")]
        for fname in sorted(files, reverse=True):
            fpath = os.path.join(LOG_DIR, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    all_logs.extend(json.load(f))
            except Exception as e:
                print(f"[Audit] Could not read log file {fname}: {e}")
        return sorted(all_logs, key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception as e:
        print(f"[Audit] get_logs error: {e}")
        return []
