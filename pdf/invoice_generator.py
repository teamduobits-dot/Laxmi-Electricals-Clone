import os
import textwrap
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from config import BUSINESS_NAME, BUSINESS_PHONE, BUSINESS_ADDRESS, RESOURCE_DIR
from database.bills_repo import get_bill_bundle
from database.settings_repo import get_business_profile
from utils.storage import get_pdf_path
from utils.formatting import smart_title


# Colors
OUTER_RED = colors.HexColor("#D32F2F")
GRID_LIGHT = colors.HexColor("#F2B8B8")
TEXT = colors.HexColor("#111827")
MUTED = colors.HexColor("#4B5563")
HEADER_BG = colors.HexColor("#F3F4F6")

# Font setup (we keep filenames as Roboto-*.ttf, but you can put Segoe UI there)
FONT_REG = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
CURRENCY = "Rs."  # will change to ₹ if font supports it

def _try_register_fonts():
    global FONT_REG, FONT_BOLD, CURRENCY
    reg_path = os.path.join(RESOURCE_DIR, "assets", "fonts", "Roboto-Regular.ttf")
    bold_path = os.path.join(RESOURCE_DIR, "assets", "fonts", "Roboto-Bold.ttf")

    if os.path.exists(reg_path) and os.path.exists(bold_path):
        try:
            pdfmetrics.registerFont(TTFont("Roboto", reg_path))
            pdfmetrics.registerFont(TTFont("Roboto-Bold", bold_path))
            FONT_REG = "Roboto"
            FONT_BOLD = "Roboto-Bold"
            CURRENCY = "₹"
        except:
            pass

_try_register_fonts()


def _money(v) -> str:
    try:
        return f"{float(v):.2f}"
    except:
        return "0.00"


def _qty(v) -> str:
    try:
        f = float(v)
        if f.is_integer():
            return str(int(f))
        return f"{f:.2f}"
    except:
        return "0"


def _title(s: str) -> str:
    # Reuse the app-wide name normalizer so acronyms (MSEB, LED, UPI...) survive on the PDF.
    return smart_title(s)


def _safe_image(c, path: str, x: float, y: float, w: float, h: float):
    if path and os.path.exists(path):
        c.drawImage(path, x, y, width=w, height=h, mask="auto")


def _center_wrapped(c, text: str, xcenter: float, y: float, max_chars: int, font: str, size: int, color=TEXT, leading=12):
    c.setFillColor(color)
    c.setFont(font, size)
    lines = textwrap.wrap(text, width=max_chars)
    for i, line in enumerate(lines[:2]):  # max 2 lines
        c.drawCentredString(xcenter, y - i * leading, line)


def _totals_metrics(bill) -> tuple:
    """
    Height of the totals box for this bill, and the bottom band height that
    fully contains it. Returns (totals_h, bottom_h).
    """
    discount = float(bill.get("discount_amount", 0) or 0)
    tax_percent = float(bill.get("tax_percent", 0) or 0)

    rows = 3  # Subtotal, Advance Paid, Balance Due
    if discount > 0:
        rows += 1
    if tax_percent > 0:
        rows += 2  # CGST + SGST split

    row_height = 18
    totals_h = (rows + 1) * row_height + 4  # +1 for the GRAND TOTAL row
    bottom_h = max(112, totals_h + 24)      # band grows so the box never overflows it
    return totals_h, bottom_h


def _page_geometry(bill) -> dict:
    """
    Single source of truth for page geometry + row capacities, shared by the
    paginator and the page renderer so items can never be clipped.
    """
    W, H = A4
    m = 24
    header_h = 108
    info_h = 80
    totals_h, bottom_h = _totals_metrics(bill)

    table_top = (H - m) - header_h - info_h
    table_bottom = m + bottom_h
    head_h = 24
    row_h = 20
    start_y = table_top - head_h - 15

    # Rows that fit given the renderer's min_y guards (see _draw_page)
    rows_full = int((start_y - (table_bottom + 12)) // row_h) + 1
    rows_last = int((start_y - (table_bottom + totals_h + 16)) // row_h) + 1

    return {
        "m": m, "header_h": header_h, "info_h": info_h,
        "totals_h": totals_h, "bottom_h": bottom_h,
        "table_top": table_top, "table_bottom": table_bottom,
        "head_h": head_h, "row_h": row_h,
        "rows_full": max(6, rows_full), "rows_last": max(6, rows_last),
    }


def _draw_page(c, bill, customer, page_items, page_number: int, total_pages: int, show_totals: bool, biz: dict, geo: dict):
    biz_name = (biz.get("name") or "").strip()
    biz_phone = (biz.get("phone") or "").strip()
    biz_address = (biz.get("address") or "").strip()

    W, H = A4
    m = geo["m"]
    x0, y0 = m, m
    x1, y1 = W - m, H - m
    header_h = geo["header_h"]
    info_h = geo["info_h"]
    bottom_h = geo["bottom_h"]

    # Outer border
    c.setStrokeColor(OUTER_RED)
    c.setLineWidth(1.6)
    c.rect(x0, y0, x1 - x0, y1 - y0)

    # ================= HEADER =================
    header_top = y1
    header_bottom = header_top - header_h
    c.setLineWidth(1.1)
    c.rect(x0, header_bottom, x1 - x0, header_h)

    # Left logo only
    left_img = os.path.join(RESOURCE_DIR, "assets", "logo_left.png")
    _safe_image(c, left_img, x0 + 10, header_bottom + 16, 78, 78)

    c.setFillColor(MUTED)
    c.setFont(FONT_REG, 9)
    c.drawCentredString((x0 + x1) / 2, header_top - 16, "CASH MEMO")
    c.drawRightString(x1 - 10, header_top - 16, f"Phone: {biz_phone}")

    c.setFillColor(OUTER_RED)
    c.setFont(FONT_BOLD, 28)
    c.drawCentredString((x0 + x1) / 2, header_top - 44, _title(biz_name))

    tagline = "Electrical Labour Contractor | Wiring | Repairs | Installation"
    _center_wrapped(c, tagline, (x0 + x1) / 2, header_top - 70, max_chars=70, font=FONT_BOLD, size=10.8, color=MUTED, leading=13)
    _center_wrapped(c, biz_address, (x0 + x1) / 2, header_top - 92, max_chars=85, font=FONT_REG, size=10.2, color=MUTED, leading=12)

    # ================= INFO BLOCK =================
    info_top = header_bottom
    info_bottom = info_top - info_h
    c.setStrokeColor(OUTER_RED)
    c.setLineWidth(1.0)
    c.rect(x0, info_bottom, x1 - x0, info_h)

    right_w = 205
    split_x = x1 - right_w
    c.line(split_x, info_bottom, split_x, info_top)

    created_at = bill.get("created_at") or ""
    try:
        dt = datetime.fromisoformat(created_at)
        date_str = dt.strftime("%d-%m-%Y")
    except:
        date_str = created_at[:10]

    # Left: customer fields
    c.setFillColor(TEXT)
    c.setFont(FONT_BOLD, 10)
    c.drawString(x0 + 12, info_top - 20, "Name:")
    c.drawString(x0 + 12, info_top - 42, "Phone:")
    c.drawString(x0 + 12, info_top - 64, "Address:")

    c.setFont(FONT_REG, 10)
    c.drawString(x0 + 62, info_top - 20, _title(customer.get("name", "")))
    c.drawString(x0 + 62, info_top - 42, (customer.get("phone") or "").strip())

    addr = ((bill.get("bill_address") or "").strip() or (customer.get("address") or "").strip()).replace("\n", " ")
    addr_lines = textwrap.wrap(addr, width=80)
    c.drawString(x0 + 74, info_top - 64, addr_lines[0] if addr_lines else "")
    if len(addr_lines) > 1:
        c.setFont(FONT_REG, 9.5)
        c.drawString(x0 + 74, info_top - 76, addr_lines[1])

    # Right: bill info
    c.setFillColor(TEXT)
    c.setFont(FONT_BOLD, 11)
    c.drawString(split_x + 12, info_top - 26, "Bill No:")
    c.setFillColor(OUTER_RED)
    c.setFont(FONT_BOLD, 16)
    c.drawString(split_x + 72, info_top - 30, bill.get("bill_number", ""))

    c.setFillColor(TEXT)
    c.setFont(FONT_BOLD, 11)
    c.drawString(split_x + 12, info_top - 52, "Date:")
    c.setFont(FONT_REG, 11)
    c.drawString(split_x + 52, info_top - 52, date_str)

    c.setFillColor(TEXT)
    c.setFont(FONT_BOLD, 10.8)
    c.drawString(split_x + 12, info_bottom + 10, f"Mode: {bill.get('payment_mode','')}")
    c.drawRightString(x1 - 12, info_bottom + 10, f"Status: {bill.get('status','')}")

    # ================= BOTTOM BAND =================
    bottom_top = y0 + bottom_h

    c.setStrokeColor(OUTER_RED)
    c.setLineWidth(1.0)
    c.rect(x0, y0, x1 - x0, bottom_h)

    c.setFillColor(MUTED)
    c.setFont(FONT_REG, 9)
    c.drawString(x0 + 10, y0 + 8, f"Page {page_number}/{total_pages}")

    # Totals box (right)
    totals_w = 240
    totals_h = 74
    tbx = x1 - totals_w - 10
    tby = y0 + 12

    if show_totals:
        c.setStrokeColor(OUTER_RED)
        c.setLineWidth(1.0)
        
        subtotal = float(bill.get("subtotal", 0) or 0)
        discount = float(bill.get("discount_amount", 0) or 0)
        tax_percent = float(bill.get("tax_percent", 0) or 0)
        tax_amount = float(bill.get("tax_amount", 0) or 0)
        advance = float(bill.get("advance_paid", 0) or 0)
        due = float(bill.get("due_amount", 0) or 0)
        total = float(bill.get("total_amount", 0) or 0)

        # Calculate number of rows needed in totals box
        rows = [("Subtotal", subtotal)]
        if discount > 0:
            rows.append(("Discount", discount))
        
        if tax_percent > 0:
            # Split GST into CGST and SGST for Indian context
            half_p = tax_percent / 2.0
            half_a = tax_amount / 2.0
            rows.append((f"CGST ({half_p}%)", half_a))
            rows.append((f"SGST ({half_p}%)", half_a))
        
        rows.append(("Advance Paid", advance))
        rows.append(("Balance Due", due))
        
        totals_w = 240
        totals_h = geo["totals_h"]  # precomputed so the box fits the band exactly
        row_height = 18
        tbx = x1 - totals_w - 10
        tby = y0 + 12

        c.rect(tbx, tby, totals_w, totals_h)

        c.setStrokeColor(GRID_LIGHT)
        c.setLineWidth(0.6)
        
        c.setFillColor(TEXT)
        c.setFont(FONT_REG, 10)
        
        for i, (label, val) in enumerate(rows):
            yy = tby + totals_h - (i + 1) * row_height
            c.drawString(tbx + 10, yy, label)
            c.drawRightString(tbx + totals_w - 10, yy, f"{CURRENCY} {_money(val)}")
            c.line(tbx, yy - 4, tbx + totals_w, yy - 4)

        # Final Total
        c.setFont(FONT_BOLD, 11)
        c.drawString(tbx + 10, tby + 6, "GRAND TOTAL")
        c.drawRightString(tbx + totals_w - 10, tby + 6, f"{CURRENCY} {_money(total)}")

        # Signature text on LEFT
        sig_x = x0 + 40
        sig_y = tby + totals_h - 10
        c.setFillColor(TEXT)
        c.setFont(FONT_BOLD, 10)
        c.drawString(sig_x, sig_y, f"For {_title(biz_name)}")
        c.setFont(FONT_REG, 10)
        c.drawString(sig_x, sig_y - 16, "Authorized Signature")

    # ================= ITEMS TABLE =================
    table_top = info_bottom
    table_bottom = bottom_top

    c.setStrokeColor(OUTER_RED)
    c.setLineWidth(1.0)
    c.rect(x0, table_bottom, x1 - x0, table_top - table_bottom)

    # Columns
    total_w = x1 - x0
    sr_w = 34
    qty_w = 55
    rate_w = 72
    amt_w = 86
    desc_w = total_w - (sr_w + qty_w + rate_w + amt_w)

    cx0 = x0
    cx1 = x0 + sr_w
    cx2 = cx1 + desc_w
    cx3 = cx2 + qty_w
    cx4 = cx3 + rate_w
    cx5 = x1

    head_h = 24
    c.setFillColor(HEADER_BG)
    c.setStrokeColor(GRID_LIGHT)
    c.setLineWidth(0.6)
    c.rect(x0, table_top - head_h, x1 - x0, head_h, stroke=1, fill=1)

    c.setStrokeColor(GRID_LIGHT)
    c.setLineWidth(0.6)
    c.line(cx1, table_bottom, cx1, table_top)
    c.line(cx2, table_bottom, cx2, table_top)
    c.line(cx3, table_bottom, cx3, table_top)
    c.line(cx4, table_bottom, cx4, table_top)

    c.setFillColor(TEXT)
    c.setFont(FONT_BOLD, 10)
    c.drawCentredString((cx0 + cx1) / 2, table_top - 17, "Sr.")
    c.drawCentredString((cx1 + cx2) / 2, table_top - 17, "Description")
    c.drawCentredString((cx2 + cx3) / 2, table_top - 17, "Qty")
    c.drawCentredString((cx3 + cx4) / 2, table_top - 17, "Rate")
    c.drawCentredString((cx4 + cx5) / 2, table_top - 17, "Amount")

    row_h = 20
    usable_h = (table_top - head_h) - (table_bottom + 10)
    rows_possible = int(usable_h // row_h)

    c.setStrokeColor(GRID_LIGHT)
    c.setLineWidth(0.5)
    c.setDash(2, 2)
    for i in range(1, rows_possible + 1):
        yy = table_top - head_h - i * row_h
        if yy > table_bottom + 10:
            c.line(x0, yy, x1, yy)
    c.setDash()

    # keep a little empty space on last page so items never touch the totals box
    min_y = table_bottom + (geo["totals_h"] + 16 if show_totals else 12)

    c.setFillColor(TEXT)
    c.setFont(FONT_REG, 10)
    start_y = table_top - head_h - 15

    for i, it in enumerate(page_items):
        yy = start_y - i * row_h
        if yy < min_y:
            break

        sr = str(it.get("_sr", i + 1))
        desc = _title(it.get("service_name", ""))[:60]
        qty = _qty(it.get("qty", 0))
        rate = _money(it.get("rate", 0))
        amt = _money(it.get("amount", 0))

        c.drawCentredString((cx0 + cx1) / 2, yy, sr)
        c.drawString(cx1 + 8, yy, desc)
        c.drawRightString(cx3 - 8, yy, qty)
        c.drawRightString(cx4 - 8, yy, rate)
        c.drawRightString(cx5 - 8, yy, amt)


def generate_invoice_pdf(bill_id: int) -> str:
    bundle = get_bill_bundle(bill_id)
    bill = bundle["bill"]
    customer = bundle["customer"] or {}
    items = bundle["items"] or []

    # Load editable business profile (from Settings table)
    biz = get_business_profile(BUSINESS_NAME, BUSINESS_PHONE, BUSINESS_ADDRESS)

    bill_number = bill.get("bill_number", "UNKNOWN")
    pdf_path = get_pdf_path(bill_number, customer_name=(customer.get("name","") if customer else ""), customer_phone=(customer.get("phone","") if customer else ""))

    items2 = []
    for i, it in enumerate(items, start=1):
        it2 = dict(it)
        it2["_sr"] = i
        items2.append(it2)

    # Pagination with clipping-safe capacities: middle pages hold rows_full items,
    # the final page (which also carries the totals box) never more than rows_last.
    geo = _page_geometry(bill)
    rows_full = geo["rows_full"]
    rows_last = geo["rows_last"]

    pages = []
    n = len(items2)
    i = 0
    while n - i > rows_last:
        remaining = n - i
        if remaining - rows_full <= 0:
            # This chunk would end up as an overfull last page: split it so the
            # final page holds exactly rows_last items.
            first = remaining - rows_last
            pages.append(items2[i:i + first])
            i += first
        else:
            pages.append(items2[i:i + rows_full])
            i += rows_full
    pages.append(items2[i:])
    if not pages:
        pages = [[]]

    c = canvas.Canvas(pdf_path, pagesize=A4)

    total_pages = len(pages)
    for p_idx, page_items in enumerate(pages, start=1):
        show_totals = (p_idx == total_pages)
        _draw_page(c, bill, customer, page_items, p_idx, total_pages, show_totals, biz=biz, geo=geo)
        c.showPage()

    c.save()
    return pdf_path












