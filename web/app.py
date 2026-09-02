"""
Laxmi Electricals Billing — Mobile Web Edition
==============================================
A mobile-browser front-end over the EXACT same business logic as the desktop app.

This module deliberately contains **no business rules**. Every calculation,
validation and PDF render is delegated to the same modules the CustomTkinter
desktop app uses:

    database/bills_repo.py          create_bill  (totals, GST, bill numbering)
    database/bills_manage_repo.py   update_bill / delete_bill / list_bills
    database/customers_repo.py      customer CRUD + phone uniqueness
    database/services_repo.py       service catalog
    database/dues_repo.py           receive_payment
    database/dashboard_repo.py      dashboard stats
    database/reports_repo.py        daily / monthly reports
    pdf/invoice_generator.py        the identical ReportLab invoice
    utils/*                         auth, validators, formatting, dates, storage

So a bill created on a phone is byte-for-byte identical to one created on the
desktop, and both read/write the same SQLite database.
"""
import os
import sys
import csv
import io
import logging

# Make the project root importable so we can reuse the desktop modules as-is.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

# ---- Reused desktop modules (single source of truth) ------------------------
import config
from database.db import init_db
from database import bills_repo, bills_manage_repo, customers_repo, services_repo
from database import dues_repo, dashboard_repo, reports_repo, lookups_repo, settings_repo
from pdf.invoice_generator import generate_invoice_pdf
from utils import auth
from utils.storage import best_pdf_path_for_bill_number, delete_pdf_files_for_bill_number
from utils.formatting import format_currency, smart_title
from utils.date_utils import fmt_date, today_ddmmyyyy, parse_ddmmyyyy_to_iso
from utils.whatsapp_share import get_whatsapp_preview_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="Laxmi Electricals Billing — Mobile")

# ---------------------------------------------------------------------------
# TESTING MODE
# ---------------------------------------------------------------------------
# When DISABLE_AUTH is on, the login screen is bypassed entirely so the app can
# be opened and clicked through without credentials.
#
#   Testing (default here):  LAXMI_DISABLE_AUTH=1
#   Production:              LAXMI_DISABLE_AUTH=0   (re-enables the login page)
#
# !! Never ship to a public URL with this enabled — it leaves the app open. !!
DISABLE_AUTH = os.getenv("LAXMI_DISABLE_AUTH", "1") not in ("0", "false", "False", "")

# Session cookie must be SameSite=None + Secure to survive being embedded in a
# cross-site HTTPS iframe (e.g. the Arena preview). With the default 'lax' the
# browser silently drops the cookie, so login appears to "fail" by bouncing
# straight back to the login page. Over plain HTTP on a LAN we keep 'lax',
# because Secure cookies are not stored on non-HTTPS origins.
_CROSS_SITE = os.getenv("LAXMI_CROSS_SITE", "1") not in ("0", "false", "False", "")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("LAXMI_SECRET", "laxmi-electricals-dev-secret"),
    max_age=60 * 60 * 12,
    same_site="none" if _CROSS_SITE else "lax",
    https_only=_CROSS_SITE,
)

if DISABLE_AUTH:
    logging.warning("AUTH DISABLED (LAXMI_DISABLE_AUTH=1) — login bypassed for testing.")

BASE = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))

templates.env.globals["money"] = format_currency
templates.env.globals["fmt_date"] = fmt_date
templates.env.globals["APP_VERSION"] = config.APP_VERSION
templates.env.globals["DISABLE_AUTH"] = DISABLE_AUTH

init_db()

PAYMENT_MODES = ("Cash", "UPI", "Bank Transfer")


# ---------------------------------------------------------------- helpers ---
def logged_in(request: Request) -> bool:
    if DISABLE_AUTH:
        return True
    return bool(request.session.get("auth"))


def guard(request: Request):
    """Raise a redirect-to-login for unauthenticated page requests."""
    if DISABLE_AUTH:
        return
    if not logged_in(request):
        raise HTTPException(status_code=307, headers={"Location": "/login"})


def page(request: Request, name: str, **ctx):
    ctx.setdefault("active", "")
    return templates.TemplateResponse(request, name, ctx)


def biz():
    return settings_repo.get_business_profile(
        config.BUSINESS_NAME, config.BUSINESS_PHONE, config.BUSINESS_ADDRESS
    )


@app.exception_handler(HTTPException)
async def http_exc(request: Request, exc: HTTPException):
    if exc.status_code == 307 and exc.headers and "Location" in exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    return HTMLResponse(f"<h3 style='font-family:sans-serif;padding:24px'>{exc.status_code}: {exc.detail}</h3>",
                        status_code=exc.status_code)


# ------------------------------------------------------------------ auth ----
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if DISABLE_AUTH or logged_in(request):
        return RedirectResponse("/", status_code=303)
    return page(request, "login.html", first_run=not auth.has_admin_password(), error=None)


@app.post("/login")
def login_submit(request: Request, password: str = Form(...), confirm: str = Form("")):
    if DISABLE_AUTH:
        return RedirectResponse("/", status_code=303)
    first = not auth.has_admin_password()
    try:
        if first:
            # First run: set the admin password (same rule as desktop: min 4 chars)
            if len(password.strip()) < 4:
                raise ValueError("Password must be at least 4 characters.")
            if password != confirm:
                raise ValueError("Passwords do not match.")
            auth.set_admin_password(password)
        elif not auth.check_login(password):
            raise ValueError("Incorrect password.")
    except ValueError as e:
        return page(request, "login.html", first_run=first, error=str(e))
    request.session["auth"] = True
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    if DISABLE_AUTH:
        return RedirectResponse("/", status_code=303)
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


# ------------------------------------------------------------- dashboard ----
@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    guard(request)
    return page(request, "dashboard.html", active="home",
                stats=dashboard_repo.get_dashboard_stats(),
                recent=dashboard_repo.get_recent_bills(6),
                top=dashboard_repo.get_top_customers(5),
                biz=biz())


# --------------------------------------------------------------- billing ----
@app.get("/billing", response_class=HTMLResponse)
def billing_form(request: Request, customer_id: int = 0):
    guard(request)
    return page(request, "billing.html", active="new",
                customers=lookups_repo.list_customers(),
                services=lookups_repo.list_services(),
                modes=PAYMENT_MODES,
                today=today_ddmmyyyy(),
                preset_customer=customer_id)


@app.post("/billing")
async def billing_submit(request: Request):
    guard(request)
    f = await request.form()
    try:
        customer_id = int(f.get("customer_id") or 0)
        if not customer_id:
            raise ValueError("Please select a customer.")

        # Collect the dynamic item rows exactly like the desktop item table.
        names = f.getlist("service_name")
        qtys = f.getlist("qty")
        rates = f.getlist("rate")
        items = []
        for n, q, r in zip(names, qtys, rates):
            if (n or "").strip():
                items.append({"service_name": n.strip(), "qty": q or 0, "rate": r or 0})
        if not items:
            raise ValueError("Add at least one service item.")

        date_str = (f.get("bill_date") or "").strip()
        custom_date = parse_ddmmyyyy_to_iso(date_str) if date_str else None
        if date_str and not custom_date:
            raise ValueError("Date must be DD-MM-YYYY.")

        # >>> identical call the desktop BillingPage makes <<<
        bill_id, bill_number = bills_repo.create_bill(
            customer_id=customer_id,
            items=items,
            advance_paid=f.get("advance") or 0,
            payment_mode=f.get("payment_mode") or "Cash",
            bill_address=f.get("bill_address") or "",
            custom_date=custom_date,
            tax_percent=f.get("tax_percent") or 0,
            discount_amount=f.get("discount") or 0,
        )

        # Optionally add any newly typed services to the catalog (desktop parity)
        if f.get("save_services"):
            for it in items:
                try:
                    services_repo.create_service(it["service_name"], float(it["rate"] or 0))
                except Exception:
                    pass  # already exists — same non-fatal behaviour as desktop

        generate_invoice_pdf(bill_id)
        return RedirectResponse(f"/bills/{bill_id}?created=1", status_code=303)

    except ValueError as e:
        return page(request, "billing.html", active="new",
                    customers=lookups_repo.list_customers(),
                    services=lookups_repo.list_services(),
                    modes=PAYMENT_MODES, today=today_ddmmyyyy(),
                    preset_customer=0, error=str(e))


# ----------------------------------------------------------------- bills ----
@app.get("/bills", response_class=HTMLResponse)
def bills_list(request: Request, q: str = "", created: str = ""):
    guard(request)
    return page(request, "bills.html", active="bills",
                bills=bills_manage_repo.list_bills(q, 120), q=q, created=created)


@app.get("/bills/{bill_id}", response_class=HTMLResponse)
def bill_detail(request: Request, bill_id: int):
    guard(request)
    try:
        b = bills_repo.get_bill_bundle(bill_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bill not found.")
    cust = b["customer"] or {}
    msg = (f"Hello {cust.get('name','')}, your bill {b['bill']['bill_number']} "
           f"from {biz()['name']} is ready. Total: Rs.{b['bill']['total_amount']:.2f}, "
           f"Balance Due: Rs.{b['bill']['due_amount']:.2f}. Thank you!")
    return page(request, "bill_detail.html", active="bills", b=b["bill"], c=cust, items=b["items"],
                wa=get_whatsapp_preview_url(cust.get("phone", ""), msg), modes=PAYMENT_MODES)


@app.get("/bills/{bill_id}/pdf")
def bill_pdf(request: Request, bill_id: int, download: int = 0):
    """
    Serve the invoice PDF.

    Notes on the headers below — these matter for mobile browsers:
      * `inline` lets the browser render it; `attachment` forces a save.
      * `X-Frame-Options: SAMEORIGIN` is NOT set, and CSP frame-ancestors is
        left open, so the PDF can be shown inside our own viewer <iframe>
        even when the whole app is itself embedded in a cross-site iframe.
      * `Accept-Ranges` lets mobile PDF viewers fetch byte ranges instead of
        refusing to render.
    """
    guard(request)
    try:
        b = bills_repo.get_bill_bundle(bill_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bill not found.")

    number = b["bill"]["bill_number"]
    path = best_pdf_path_for_bill_number(number)
    if not path or not os.path.exists(path) or os.path.getsize(path) == 0:
        # regenerate-if-missing (or if a previous run left a 0-byte file)
        path = generate_invoice_pdf(bill_id)

    if not path or not os.path.exists(path):
        raise HTTPException(status_code=500, detail="Invoice PDF could not be generated.")

    disp = "attachment" if download else "inline"
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disp}; filename="{number}.pdf"',
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/bills/{bill_id}/invoice", response_class=HTMLResponse)
def bill_invoice_view(request: Request, bill_id: int):
    """
    A viewer page for the invoice.

    Why this exists: `target="_blank"` links are frequently blocked when the
    app runs inside a sandboxed iframe, and many mobile browsers refuse to
    render `application/pdf` inline at all — both look to the user like
    "the PDF doesn't open". This page always renders *something*: an embedded
    preview where supported, plus explicit Download / Open-in-new-tab buttons
    that work everywhere.
    """
    guard(request)
    try:
        b = bills_repo.get_bill_bundle(bill_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bill not found.")
    return page(request, "invoice_view.html", active="bills",
                b=b["bill"], c=b["customer"] or {})



@app.post("/bills/{bill_id}/pay")
def bill_pay(request: Request, bill_id: int, amount: float = Form(...), payment_mode: str = Form("Cash")):
    guard(request)
    try:
        dues_repo.receive_payment(bill_id, amount, payment_mode)
        generate_invoice_pdf(bill_id)  # refresh PDF after collection, same as desktop
    except Exception as e:
        return RedirectResponse(f"/bills/{bill_id}?err={e}", status_code=303)
    return RedirectResponse(f"/bills/{bill_id}?paid=1", status_code=303)


@app.post("/bills/{bill_id}/delete")
def bill_delete(request: Request, bill_id: int):
    guard(request)
    try:
        number = bills_repo.get_bill_bundle(bill_id)["bill"]["bill_number"]
    except ValueError:
        raise HTTPException(status_code=404, detail="Bill not found.")
    bills_manage_repo.delete_bill(bill_id)
    delete_pdf_files_for_bill_number(number)  # remove PDFs too, same as desktop
    return RedirectResponse("/bills", status_code=303)


@app.get("/bills/{bill_id}/edit", response_class=HTMLResponse)
def bill_edit_form(request: Request, bill_id: int):
    guard(request)
    try:
        b = bills_repo.get_bill_bundle(bill_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bill not found.")
    return page(request, "bill_edit.html", active="bills", b=b["bill"], items=b["items"],
                customers=lookups_repo.list_customers(), services=lookups_repo.list_services(),
                modes=PAYMENT_MODES)


@app.post("/bills/{bill_id}/edit")
async def bill_edit_submit(request: Request, bill_id: int):
    guard(request)
    f = await request.form()
    try:
        items = [{"service_name": n.strip(), "qty": q or 0, "rate": r or 0}
                 for n, q, r in zip(f.getlist("service_name"), f.getlist("qty"), f.getlist("rate"))
                 if (n or "").strip()]
        bills_manage_repo.update_bill(
            bill_id=bill_id,
            customer_id=int(f.get("customer_id") or 0),
            items=items,
            advance_paid=f.get("advance") or 0,
            payment_mode=f.get("payment_mode") or "Cash",
            tax_percent=f.get("tax_percent") or 0,
            discount_amount=f.get("discount") or 0,
            bill_address=f.get("bill_address") or "",
        )
        generate_invoice_pdf(bill_id)
    except ValueError as e:
        b = bills_repo.get_bill_bundle(bill_id)
        return page(request, "bill_edit.html", active="bills", b=b["bill"], items=b["items"],
                    customers=lookups_repo.list_customers(), services=lookups_repo.list_services(),
                    modes=PAYMENT_MODES, error=str(e))
    return RedirectResponse(f"/bills/{bill_id}", status_code=303)


# ------------------------------------------------------------- customers ----
@app.get("/customers", response_class=HTMLResponse)
def customers_list(request: Request, q: str = ""):
    guard(request)
    return page(request, "customers.html", active="more",
                customers=customers_repo.search_customers(q, 100, 0), q=q)


@app.post("/customers")
async def customers_create(request: Request):
    guard(request)
    f = await request.form()
    cid = f.get("id")
    try:
        if cid:
            customers_repo.update_customer(int(cid), f.get("name", ""), f.get("phone", ""), f.get("address", ""))
        else:
            customers_repo.create_customer(f.get("name", ""), f.get("phone", ""), f.get("address", ""))
    except ValueError as e:
        return page(request, "customers.html", active="more",
                    customers=customers_repo.search_customers("", 100, 0), q="", error=str(e))
    return RedirectResponse("/customers", status_code=303)


@app.post("/customers/{cid}/delete")
def customers_delete(request: Request, cid: int):
    guard(request)
    try:
        customers_repo.delete_customer(cid)
    except ValueError as e:
        return page(request, "customers.html", active="more",
                    customers=customers_repo.search_customers("", 100, 0), q="", error=str(e))
    return RedirectResponse("/customers", status_code=303)


@app.post("/api/customers")
async def api_quick_customer(request: Request):
    """Quick-add used by the billing screen's modal (matches desktop Quick Add)."""
    guard(request)
    f = await request.form()
    try:
        cid = customers_repo.create_customer(f.get("name", ""), f.get("phone", ""), f.get("address", ""))
        c = customers_repo.get_customer(cid)
        return JSONResponse({"ok": True, "id": cid, "name": c["name"], "phone": c["phone"]})
    except ValueError as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=400)


# -------------------------------------------------------------- services ----
@app.get("/services", response_class=HTMLResponse)
def services_list(request: Request, q: str = ""):
    guard(request)
    rows = [dict(r) for r in services_repo.search_services(q)]
    for r in rows:
        r["usage_count"] = services_repo.service_usage_count(r["id"])
    return page(request, "services.html", active="more", services=rows, q=q)


@app.post("/services")
async def services_create(request: Request):
    guard(request)
    f = await request.form()
    sid = f.get("id")
    try:
        if sid:
            services_repo.update_service(int(sid), f.get("service_name", ""), float(f.get("default_price") or 0))
        else:
            services_repo.create_service(f.get("service_name", ""), float(f.get("default_price") or 0))
    except ValueError as e:
        return page(request, "services.html", active="more", services=services_repo.search_services(""), q="", error=str(e))
    return RedirectResponse("/services", status_code=303)


@app.post("/services/{sid}/delete")
def services_delete(request: Request, sid: int):
    guard(request)
    services_repo.delete_service(sid)
    return RedirectResponse("/services", status_code=303)


# ------------------------------------------------------------------ dues ----
@app.get("/dues", response_class=HTMLResponse)
def dues_list(request: Request, q: str = "", customer_id: int = 0):
    guard(request)
    rows = dues_repo.list_due_bills(q, customer_id or None, 200)
    return page(request, "dues.html", active="dues", dues=rows, q=q,
                customers=dues_repo.list_customers_for_filter(), customer_id=customer_id,
                total=sum(float(r["due_amount"] or 0) for r in rows), modes=PAYMENT_MODES)


@app.post("/dues/{bill_id}/collect")
def dues_collect(request: Request, bill_id: int, amount: float = Form(...), payment_mode: str = Form("Cash")):
    guard(request)
    try:
        dues_repo.receive_payment(bill_id, amount, payment_mode)
        generate_invoice_pdf(bill_id)
    except Exception as e:
        return RedirectResponse(f"/dues?err={e}", status_code=303)
    return RedirectResponse("/dues?collected=1", status_code=303)


# --------------------------------------------------------------- reports ----
@app.get("/reports", response_class=HTMLResponse)
def reports(request: Request, mode: str = "daily", date: str = "", year: int = 0, month: int = 0):
    guard(request)
    from datetime import datetime
    now = datetime.now()
    date = date or now.strftime("%Y-%m-%d")
    year = year or now.year
    month = month or now.month
    if mode == "monthly":
        summary, rows = reports_repo.monthly_summary(year, month), reports_repo.monthly_bills(year, month)
    else:
        summary, rows = reports_repo.daily_summary(date), reports_repo.daily_bills(date)
    return page(request, "reports.html", active="more", mode=mode, summary=summary, rows=rows,
                date=date, year=year, month=month, years=reports_repo.available_years() or [now.year])


@app.get("/reports/export")
def reports_export(request: Request, mode: str = "daily", date: str = "", year: int = 0, month: int = 0):
    guard(request)
    rows = reports_repo.monthly_bills(year, month) if mode == "monthly" else reports_repo.daily_bills(date)
    rows = [dict(r) for r in rows]
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    label = f"{year}-{month:02d}" if mode == "monthly" else date
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="report_{label}.csv"'})


# -------------------------------------------------------------- settings ----
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, saved: str = "", error: str = ""):
    guard(request)
    return page(request, "settings.html", active="more", biz=biz(), info=config.get_app_info(),
                saved=saved, error=error)


@app.post("/settings/business")
def settings_business(request: Request, name: str = Form(""), phone: str = Form(""), address: str = Form("")):
    guard(request)
    settings_repo.save_business_profile(name, phone, address)
    return RedirectResponse("/settings?saved=Business+profile+updated", status_code=303)


@app.post("/settings/password")
def settings_password(request: Request, current: str = Form(...), new: str = Form(...)):
    guard(request)
    try:
        auth.change_admin_password(current, new)
    except ValueError as e:
        return RedirectResponse(f"/settings?error={e}", status_code=303)
    return RedirectResponse("/settings?saved=Password+changed", status_code=303)


@app.post("/settings/backup")
def settings_backup(request: Request):
    guard(request)
    from utils.backup import create_local_backup
    try:
        path = create_local_backup()
        return RedirectResponse(f"/settings?saved=Backup+created:+{os.path.basename(path)}", status_code=303)
    except Exception as e:
        return RedirectResponse(f"/settings?error={e}", status_code=303)


@app.get("/more", response_class=HTMLResponse)
def more(request: Request):
    guard(request)
    return page(request, "more.html", active="more", biz=biz())


@app.get("/health")
def health():
    return {"ok": True, "version": config.APP_VERSION}
