import os
import shutil
import logging
import time
from datetime import datetime
from config import DB_PATH, BACKUP_DIR

def create_local_backup() -> str:
    """
    Creates a copy of the database file in the backups directory.
    Returns the path to the backup file.
    Uses SQLite backup API for safety if possible, otherwise file copy.
    """
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database file not found at {DB_PATH}")

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"laxmi_billing_backup_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        # Try to use sqlite backup for consistency (in case DB locked)
        import sqlite3
        src = sqlite3.connect(DB_PATH)
        dst = sqlite3.connect(backup_path)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        # Verify backup not empty
        if os.path.getsize(backup_path) == 0:
            raise ValueError("Backup file is empty, retrying with file copy")
    except Exception as e:
        logging.warning(f"SQLite backup failed ({e}), falling back to file copy")
        try:
            # Fallback file copy - try copy with retries for locked file
            for attempt in range(3):
                try:
                    shutil.copy2(DB_PATH, backup_path)
                    break
                except PermissionError:
                    time.sleep(0.5)
                    if attempt == 2:
                        raise
        except Exception as ce:
            logging.error(f"Failed to create local backup: {ce}")
            raise ce

    logging.info(f"Local backup created at {backup_path} ({os.path.getsize(backup_path)} bytes)")
    return backup_path

def list_backups():
    """Returns a list of backup files sorted by date (newest first)."""
    if not os.path.exists(BACKUP_DIR):
        return []
    try:
        files = [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith(".db")]
        files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return files
    except Exception as e:
        logging.warning(f"list_backups failed: {e}")
        return []

def cleanup_old_backups(keep_count: int = 10):
    """Deletes old backups keeping only the most recent N."""
    try:
        backups = list_backups()
        if len(backups) > keep_count:
            for old_backup in backups[keep_count:]:
                try:
                    os.remove(old_backup)
                    logging.info(f"Cleaned up old backup: {old_backup}")
                except Exception as e:
                    logging.warning(f"Failed to delete old backup {old_backup}: {e}")
    except Exception as e:
        logging.warning(f"cleanup_old_backups failed: {e}")

def get_backup_info():
    """Returns dict with backup stats"""
    backups = list_backups()
    if not backups:
        return {"count": 0, "latest": None, "total_size_mb": 0}
    total = sum(os.path.getsize(p) for p in backups if os.path.exists(p)) / (1024*1024)
    return {
        "count": len(backups),
        "latest": backups[0],
        "latest_time": os.path.getmtime(backups[0]),
        "total_size_mb": round(total, 2)
    }
