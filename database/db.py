import os
import sqlite3
import logging
from config import DB_PATH, RESOURCE_DIR

def get_connection():
    try:
        con = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys = ON;")
        con.execute("PRAGMA journal_mode=WAL;")  # Better concurrency
        con.execute("PRAGMA synchronous=NORMAL;")
        return con
    except Exception as e:
        logging.error(f"Failed to connect to DB {DB_PATH}: {e}")
        raise

def _column_exists(con, table: str, column: str) -> bool:
    try:
        rows = con.execute(f"PRAGMA table_info({table});").fetchall()
        cols = [r["name"] for r in rows]
        return column in cols
    except Exception:
        return False

def _table_exists(con, table: str) -> bool:
    try:
        row = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,)).fetchone()
        return row is not None
    except Exception:
        return False

def _ensure_migrations(con):
    # Ensure Bills table exists first
    if not _table_exists(con, "Bills"):
        return

    # Add bill_address if missing
    if not _column_exists(con, "Bills", "bill_address"):
        try:
            con.execute("ALTER TABLE Bills ADD COLUMN bill_address TEXT;")
            logging.info("Migration: Added bill_address column")
        except Exception as e:
            logging.warning(f"Migration failed bill_address: {e}")

    # Professional Billing Update: GST and Discounts
    if not _column_exists(con, "Bills", "tax_percent"):
        try:
            con.execute("ALTER TABLE Bills ADD COLUMN tax_percent REAL DEFAULT 0;")
            logging.info("Migration: Added tax_percent column")
        except Exception as e:
            logging.warning(f"Migration failed tax_percent: {e}")
    if not _column_exists(con, "Bills", "tax_amount"):
        try:
            con.execute("ALTER TABLE Bills ADD COLUMN tax_amount REAL DEFAULT 0;")
            logging.info("Migration: Added tax_amount column")
        except Exception as e:
            logging.warning(f"Migration failed tax_amount: {e}")
    if not _column_exists(con, "Bills", "discount_amount"):
        try:
            con.execute("ALTER TABLE Bills ADD COLUMN discount_amount REAL DEFAULT 0;")
            logging.info("Migration: Added discount_amount column")
        except Exception as e:
            logging.warning(f"Migration failed discount_amount: {e}")

    # Ensure indexes for performance
    try:
        con.execute("CREATE INDEX IF NOT EXISTS idx_bills_customer ON Bills(customer_id);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_bills_created ON Bills(created_at);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_bills_number ON Bills(bill_number);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_bills_due ON Bills(due_amount);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_customers_phone ON Customers(phone);")
        con.execute("CREATE INDEX IF NOT EXISTS idx_bill_items_bill ON Bill_Items(bill_id);")
    except Exception as e:
        logging.warning(f"Index creation failed: {e}")

def init_db():
    schema_path = os.path.join(RESOURCE_DIR, "database", "schema.sql")
    if not os.path.exists(schema_path):
        # Fallback to project dir
        alt = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "schema.sql")
        if os.path.exists(alt):
            schema_path = alt
        else:
            raise FileNotFoundError(f"schema.sql not found at: {schema_path} or {alt}")

    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()

    con = get_connection()
    try:
        con.executescript(sql)
        _ensure_migrations(con)
        con.commit()
        logging.info("Database initialized successfully")
    except Exception as e:
        logging.error(f"DB init failed: {e}")
        con.rollback()
        raise
    finally:
        con.close()

def vacuum_db():
    """Optimize DB"""
    con = get_connection()
    try:
        con.execute("VACUUM;")
        con.commit()
        logging.info("Database vacuumed")
    except Exception as e:
        logging.warning(f"Vacuum failed: {e}")
    finally:
        con.close()
