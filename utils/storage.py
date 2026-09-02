import os
import re
import logging
from config import BILLS_DIR
from database.settings_repo import get_setting
from database.db import get_connection
from utils.formatting import smart_title

INVALID_CHARS = r'<>:"/\\|?*'

def _sanitize(text: str, max_len: int = 60) -> str:
    s = smart_title(text or "").strip()
    s = re.sub(f"[{re.escape(INVALID_CHARS)}]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    s = s.rstrip(". ").strip()
    if not s:
        s = "Unknown"
    # Remove trailing spaces and dots that Windows disallows
    s = s.strip()
    return s[:max_len]

def get_bills_base_dir() -> str:
    base = (get_setting("bills_base_dir", "") or "").strip()
    if not base:
        base = BILLS_DIR
    try:
        os.makedirs(base, exist_ok=True)
    except Exception as e:
        logging.warning(f"Could not create bills dir {base}: {e}")
        # Fallback to default
        base = BILLS_DIR
        os.makedirs(base, exist_ok=True)
    return base

def _customer_folder(customer_name: str, customer_phone: str = "") -> str:
    name_part = _sanitize(customer_name, max_len=60)
    phone = "".join(ch for ch in (customer_phone or "") if ch.isdigit())[-10:]  # last 10 digits
    return f"{name_part} - {phone}" if phone else name_part

def get_pdf_path(
    bill_number: str,
    customer_name: str | None = None,
    customer_phone: str = "",
) -> str:
    """
    Returns:
      BillsBase/<CustomerFolder>/YYYY/<BillNo> - <CustomerName>.pdf

    If customer_name not provided, it will lookup using bill_number.
    """
    bill_number = (bill_number or "").strip()
    if not bill_number:
        raise ValueError("bill_number is required")

    year = bill_number.split("-")[0] if "-" in bill_number else "UnknownYear"

    # Lookup if needed
    if not customer_name:
        try:
            con = get_connection()
            try:
                row = con.execute(
                    """
                    SELECT c.name AS customer_name, c.phone AS customer_phone
                    FROM Bills b
                    JOIN Customers c ON c.id = b.customer_id
                    WHERE b.bill_number = ?
                    LIMIT 1;
                    """,
                    (bill_number,)
                ).fetchone()
                if row:
                    customer_name = row["customer_name"] or ""
                    customer_phone = row["customer_phone"] or ""
                else:
                    customer_name = "Unknown Customer"
            finally:
                con.close()
        except Exception as e:
            logging.warning(f"Lookup failed for bill {bill_number}: {e}")
            customer_name = customer_name or "Unknown Customer"

    base = get_bills_base_dir()
    cust_folder = _customer_folder(customer_name, customer_phone)

    year_dir = os.path.join(base, cust_folder, str(year))
    try:
        os.makedirs(year_dir, exist_ok=True)
    except Exception as e:
        logging.warning(f"Could not create year dir {year_dir}: {e}")

    safe_name = _sanitize(customer_name, max_len=50)
    filename = f"{bill_number} - {safe_name}.pdf"

    return os.path.join(year_dir, filename)

def find_pdf_files_for_bill_number(bill_number: str):
    """
    Finds PDFs for a bill number in:
      BillsBase/<CustomerFolder>/<Year>/{bill_number}*.pdf
    Also supports legacy:
      BillsBase/<Year>/{bill_number}*.pdf
    Returns list of full paths.
    """
    bill_number = (bill_number or "").strip()
    if not bill_number:
        return []

    year = bill_number.split("-")[0] if "-" in bill_number else ""
    base = get_bills_base_dir()
    matches = []

    def scan_year_dir(year_dir: str):
        if not year_dir or not os.path.isdir(year_dir):
            return
        try:
            for fn in os.listdir(year_dir):
                if fn.lower().endswith(".pdf") and fn.startswith(bill_number):
                    full = os.path.join(year_dir, fn)
                    # Validate file not empty stale
                    try:
                        if os.path.getsize(full) > 0:
                            matches.append(full)
                    except:
                        matches.append(full)
        except Exception as e:
            logging.debug(f"Scan failed for {year_dir}: {e}")

    # Legacy location: base/year/
    if year:
        scan_year_dir(os.path.join(base, year))

    # Customer folders: base/<customer>/year/
    try:
        if os.path.isdir(base):
            for cust in os.listdir(base):
                cust_path = os.path.join(base, cust)
                if not os.path.isdir(cust_path):
                    continue
                cust_year_dir = os.path.join(cust_path, year) if year else ""
                scan_year_dir(cust_year_dir)
                # Also check customer folder directly (no year sub)
                if not year:
                    scan_year_dir(cust_path)
    except Exception as e:
        logging.debug(f"Scan customer folders failed: {e}")

    # sort latest first
    try:
        matches.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    except Exception:
        pass

    # Deduplicate
    seen = set()
    uniq = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            uniq.append(m)
    return uniq

def delete_pdf_files_for_bill_number(bill_number: str) -> int:
    files = find_pdf_files_for_bill_number(bill_number)
    deleted = 0
    for p in files:
        try:
            os.remove(p)
            deleted += 1
            logging.info(f"Deleted PDF: {p}")
        except Exception as e:
            logging.warning(f"Failed to delete {p}: {e}")
    return deleted

def best_pdf_path_for_bill_number(bill_number: str):
    """
    Returns an existing path if found, else None.
    """
    files = find_pdf_files_for_bill_number(bill_number)
    return files[0] if files else None

def get_customer_pdfs(customer_name: str, customer_phone: str = ""):
    """Get all PDFs for a customer (useful for customer history)"""
    base = get_bills_base_dir()
    cust_folder = _customer_folder(customer_name, customer_phone)
    cust_path = os.path.join(base, cust_folder)
    if not os.path.isdir(cust_path):
        return []
    pdfs = []
    for root, _, files in os.walk(cust_path):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    pdfs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return pdfs
