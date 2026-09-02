from datetime import datetime
import re

def fmt_date(value: str) -> str:
    """
    Input examples:
      2026-03-03T21:10:00  (ISO)
      2026-03-03           (date)
      03-03-2026           (already formatted)
    Output:
      03-03-2026
    """
    if not value:
        return ""

    s = str(value).strip()
    if not s:
        return ""

    # If already dd-mm-yyyy
    if len(s) >= 10 and re.match(r"\d{2}-\d{2}-\d{4}", s[:10]):
        return s[:10]

    # If already dd/mm/yyyy
    if len(s) >= 10 and re.match(r"\d{2}/\d{2}/\d{4}", s[:10]):
        return s[:10].replace("/", "-")

    # Try ISO first (with T)
    try:
        # Handle Z suffix
        iso = s.replace("Z", "")
        # Try fromisoformat
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d-%m-%Y")
    except:
        pass

    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(s[:19], fmt)
            return dt.strftime("%d-%m-%Y")
        except:
            continue

    # Fallback: return first 10 chars
    return s[:10]

def fmt_datetime(value: str) -> str:
    """Return DD-MM-YYYY HH:MM"""
    if not value:
        return ""
    s = str(value).strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z",""))
        return dt.strftime("%d-%m-%Y %H:%M")
    except:
        try:
            # Try parse
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
                try:
                    dt = datetime.strptime(s[:19], fmt)
                    return dt.strftime("%d-%m-%Y %H:%M")
                except:
                    continue
        except:
            pass
    return fmt_date(s)

def today_ddmmyyyy() -> str:
    return datetime.now().strftime("%d-%m-%Y")

def today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def parse_ddmmyyyy_to_iso(date_str: str, with_time: bool = True) -> str | None:
    """Convert DD-MM-YYYY to ISO YYYY-MM-DDTHH:MM:SS"""
    try:
        dt = datetime.strptime(date_str.strip(), "%d-%m-%Y")
        if with_time:
            now = datetime.now().time()
            dt = datetime.combine(dt.date(), now)
            return dt.isoformat(timespec="seconds")
        return dt.date().isoformat()
    except:
        return None

def days_ago(days: int) -> str:
    from datetime import timedelta
    dt = datetime.now() - timedelta(days=days)
    return dt.strftime("%d-%m-%Y")

def is_date_in_current_month(iso_date_str: str) -> bool:
    try:
        dt = datetime.fromisoformat(iso_date_str.replace("Z",""))
        now = datetime.now()
        return dt.year == now.year and dt.month == now.month
    except:
        return False
