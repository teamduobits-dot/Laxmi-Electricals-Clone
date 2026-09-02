import os
import sys
import shutil
import logging
from datetime import datetime

APP_NAME = "Laxmi Electricals Billing"
APP_VERSION = "1.1.0"
APP_SUBTITLE = "Professional Edition"

BUSINESS_NAME = "Laxmi Electricals"
BUSINESS_PHONE = "9999999999"
BUSINESS_ADDRESS = "Sector No. 1338, Suyog Colony, More Wasti, Ashtvinayak Chowk, Pune - 62"

def program_dir():
    # directory containing the running script/exe (NOT where bundled resources may be)
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

PROGRAM_DIR = program_dir()

def resource_dir():
    """
    In PyInstaller builds:
      sys._MEIPASS points to extracted/bundled resources (often ...\\_internal)
    In dev:
      use project folder
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return PROGRAM_DIR

RESOURCE_DIR = resource_dir()

def app_data_dir():
    # Cross-platform app data
    if sys.platform == "win32":
        appdata = os.getenv("APPDATA")
        if not appdata:
            appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
        return os.path.join(appdata, "LaxmiElectricalsBilling")
    else:
        # Linux/Mac fallback
        return os.path.join(os.path.expanduser("~"), ".laxmi_billing")

DATA_DIR = app_data_dir()
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
LOG_DIR = os.path.join(DATA_DIR, "logs")
EXPORTS_DIR = os.path.join(DATA_DIR, "exports")

# Fallback bills folder (if user does not choose Drive folder)
BILLS_DIR = os.path.join(DATA_DIR, "bills")

DB_PATH = os.path.join(DATA_DIR, "app.db")
LOG_PATH = os.path.join(LOG_DIR, "app.log")

def ensure_app_folders():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        os.makedirs(BILLS_DIR, exist_ok=True)
        os.makedirs(EXPORTS_DIR, exist_ok=True)
    except Exception as e:
        print(f"Failed to ensure folders: {e}")

def migrate_old_db_if_needed():
    # if old DB exists in program folder and AppData DB doesn't exist yet, copy it
    old_db = os.path.join(PROGRAM_DIR, "app.db")
    if os.path.exists(old_db) and not os.path.exists(DB_PATH):
        try:
            ensure_app_folders()
            shutil.copy2(old_db, DB_PATH)
            logging.info(f"Migrated old DB from {old_db} to {DB_PATH}")
        except Exception as e:
            logging.warning(f"Failed to migrate old DB: {e}")

def backup_db() -> str | None:
    """Simple backup for internal use, returns path or None"""
    try:
        if os.path.exists(DB_PATH):
            ensure_app_folders()
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst = os.path.join(BACKUP_DIR, f"app_backup_{ts}.db")
            shutil.copy2(DB_PATH, dst)
            return dst
    except Exception as e:
        logging.warning(f"backup_db failed: {e}")
    return None

def get_app_info():
    """Returns dict with app paths for debugging"""
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "program_dir": PROGRAM_DIR,
        "resource_dir": RESOURCE_DIR,
        "data_dir": DATA_DIR,
        "db_path": DB_PATH,
        "bills_dir": BILLS_DIR,
        "backup_dir": BACKUP_DIR,
        "log_path": LOG_PATH,
    }

# Initialize on import
ensure_app_folders()
migrate_old_db_if_needed()
