import re

def smart_title(text: str) -> str:
    """
    Converts: "raHUL khAN" -> "Rahul Khan"
    Keeps very short ALLCAPS words like UPI, GST, CGST, SGST if <=4 letters and known.
    Handles multiple spaces, hyphenated names.
    """
    s = (text or "").strip()
    if not s:
        return ""

    # Preserve known abbreviations
    preserve = {"UPI", "GST", "CGST", "SGST", "IGST", "PAN", "MSEB", "LED", "PUNE", "AC", "DC"}

    words = s.split()
    out = []
    for w in words:
        # Handle hyphenated
        if "-" in w:
            parts = w.split("-")
            new_parts = []
            for p in parts:
                if p.upper() in preserve or (p.isupper() and len(p) <= 4):
                    new_parts.append(p.upper() if p.upper() in preserve else p.capitalize())
                else:
                    new_parts.append(p[:1].upper() + p[1:].lower() if p else "")
            out.append("-".join(new_parts))
        else:
            upper = w.upper()
            if upper in preserve:
                out.append(upper)
            elif w.isupper() and len(w) <= 3:
                out.append(w)  # Keep short caps
            else:
                out.append(w[:1].upper() + w[1:].lower() if w else "")
    result = " ".join(out)
    # Collapse multiple spaces
    result = re.sub(r"\s+", " ", result).strip()
    return result

def format_phone_display(phone: str) -> str:
    """Format 10-digit phone as XXXX-XXXX-XX or similar for display"""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())[-10:]
    if len(digits) == 10:
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    return phone or ""

def truncate(text: str, max_len: int = 50, suffix: str = "...") -> str:
    """Safely truncate with suffix"""
    s = (text or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - len(suffix)].strip() + suffix

def format_currency(amount: float, with_symbol: bool = True) -> str:
    try:
        val = float(amount or 0)
        if with_symbol:
            return f"₹{val:,.2f}"
        return f"{val:,.2f}"
    except:
        return "₹0.00" if with_symbol else "0.00"
