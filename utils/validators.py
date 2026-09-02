import re

def clean_phone(s: str) -> str:
    """Return only digits, max 10, keep last 10 if longer (strip country code)"""
    digits = "".join(ch for ch in (s or "") if ch.isdigit())
    # If 11-12 digits with leading 0 or 91, take last 10
    if len(digits) > 10:
        digits = digits[-10:]
    return digits[:10]

def is_valid_phone(s: str) -> bool:
    p = clean_phone(s)
    # Basic Indian mobile validation: starts with 6-9
    return len(p) == 10 and p[0] in "6789"

def sanitize_phone_entry(entry_widget):
    """Live sanitize for CTkEntry: keeps only digits, max 10"""
    try:
        p = clean_phone(entry_widget.get())
        current = entry_widget.get()
        if current != p:
            # Preserve cursor position roughly
            pos = entry_widget.index("insert")
            entry_widget.delete(0, "end")
            entry_widget.insert(0, p)
            try:
                entry_widget.icursor(min(pos, len(p)))
            except:
                pass
    except Exception:
        pass

def is_valid_amount(s: str, allow_zero: bool = True, max_value: float = 10_000_000) -> tuple[bool, float]:
    """Validate numeric amount string"""
    try:
        val = float((s or "").strip() or 0)
        if not allow_zero and val <= 0:
            return False, 0.0
        if val < 0:
            return False, 0.0
        if val > max_value:
            return False, 0.0
        return True, val
    except:
        return False, 0.0

def is_valid_gst(percent_str: str) -> tuple[bool, float]:
    try:
        val = float((percent_str or "").strip() or 0)
        if val < 0 or val > 100:
            return False, 0.0
        return True, val
    except:
        return False, 0.0

def is_valid_date_ddmmyyyy(date_str: str) -> bool:
    """Check DD-MM-YYYY format"""
    try:
        from datetime import datetime
        datetime.strptime(date_str.strip(), "%d-%m-%Y")
        return True
    except:
        return False

def sanitize_rate_entry(entry_widget):
    """Allow only numbers and dot, max one dot"""
    try:
        val = entry_widget.get()
        # Keep digits and dot
        cleaned = re.sub(r"[^0-9.]", "", val)
        # Only one dot
        if cleaned.count(".") > 1:
            parts = cleaned.split(".")
            cleaned = parts[0] + "." + "".join(parts[1:])
        if val != cleaned:
            pos = entry_widget.index("insert")
            entry_widget.delete(0, "end")
            entry_widget.insert(0, cleaned)
            try:
                entry_widget.icursor(min(pos, len(cleaned)))
            except:
                pass
    except:
        pass
