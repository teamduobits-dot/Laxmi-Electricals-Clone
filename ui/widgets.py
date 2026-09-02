import customtkinter as ctk
from ui.theme import FONT_FAMILY

def _norm(status: str) -> str:
    s = (status or "").strip().lower()
    if s in ("paid", "complete", "completed"):
        return "Paid"
    if s in ("partial", "part", "partially paid", "partially"):
        return "Partial"
    if s in ("due", "pending", "unpaid", "overdue"):
        return "Due"
    return (status or "").strip().title() or "—"

def status_colors(status: str):
    s = _norm(status)
    # (light, dark) for bg, text
    if s == "Paid":
        return (("#DCFCE7", "#064E3B"), ("#166534", "#A7F3D0"))  # green
    if s == "Partial":
        return (("#FEF9C3", "#713F12"), ("#854D0E", "#FDE68A"))  # yellow
    if s == "Due":
        return (("#FEE2E2", "#7F1D1D"), ("#991B1B", "#FCA5A5"))  # soft red
    return (("#E5E7EB", "#374151"), ("#111827", "#E5E7EB"))

def style_status_label(lbl: ctk.CTkLabel, status: str):
    text = _norm(status)
    (bg_light, bg_dark), (tx_light, tx_dark) = status_colors(text)

    # Map to dot indicator
    dot_map = {"Paid": "✓", "Partial": "◐", "Due": "●"}
    dot = dot_map.get(text, "")
    display = f"{dot} {text}" if dot else text

    lbl.configure(
        text=display,
        fg_color=(bg_light, bg_dark),
        text_color=(tx_light, tx_dark),
        corner_radius=999,
        width=88,
        height=24,
        anchor="center",
        font=ctk.CTkFont(family=FONT_FAMILY, size=10, weight="bold"),
    )
    return lbl

def style_amount_label(lbl: ctk.CTkLabel, amount: float, threshold: float = 0):
    """Color code amount - red if due, green if paid"""
    try:
        amt = float(amount or 0)
        if amt <= threshold:
            lbl.configure(text_color=("#9CA3AF", "#6B7280"))
        elif amt > 10000:
            lbl.configure(text_color=("#DC2626", "#F87171"))
        else:
            lbl.configure(text_color=("#0F172A", "#E5E7EB"))
    except:
        pass
    return lbl
