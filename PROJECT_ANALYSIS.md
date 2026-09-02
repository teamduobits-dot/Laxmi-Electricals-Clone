# Laxmi Electricals Billing — Independent Project Analysis

**Analysis date:** 2026-09-02
**Analyzed artifact:** `laxmi-electricals-billing-main (1).zip` (the only content in this repo)
**Version:** 1.1.0 "Professional Edition" · 6,174 lines of Python across 36 modules
**Method:** static reading of every module **plus** headless execution of the data + PDF layers in a throwaway SQLite DB. Every claim below marked ✅/❌ was executed, not assumed.

---

## 0. Repository state (read this first)

This repo (`teamduobits-dot/Laxmi-Electricals-Clone`) contains **exactly one file**: a 1.9 MB zip archive, committed as `Add files via upload`. There is no working tree, no CI, no packaging — the source only exists inside the zip.

**Recommendation:** extract the archive to the repo root and commit the tree. A zip in Git is opaque: no diffs, no blame, no code review, no PR comments, and every change re-uploads 1.9 MB as a new binary blob. This is the single highest-value change to make.

Note the zip also ships its own `ANALYSIS.md`. I treated it as a claim sheet, not evidence, and re-verified it — findings in §5.

---

## 1. What the project is

A single-user **Windows desktop billing app** for an electrical labour contractor in Pune. It covers the full lifecycle: customer master → services catalog → invoice creation with GST/discount/advance → ReportLab PDF invoice → bill history & edit → pending-dues collection → dashboard & reports → local + Google Drive backup.

Distribution is PyInstaller + Inno Setup, installed per-user. Data lives in `%APPDATA%\LaxmiElectricalsBilling\` (`app.db`, `backups\`, `logs\`, `exports\`, `bills\`), with a `~/.laxmi_billing/` fallback on Linux/macOS.

---

## 2. Architecture

```
main.py  (CTk root: logging, theme, login↔shell routing)
 ├── LoginFrame   ui/login.py      first-run password setup / login
 └── AppShell     ui/shell.py      sidebar + topbar + lazy page switching
      ├── Dashboard · Customers · Services · Billing
      └── Bills · Dues · Reports · Settings

database/   raw sqlite3 + Row factory, one *_repo.py per domain, schema.sql
utils/      auth (bcrypt) · storage (PDF paths) · validators · formatting
            date_utils · backup · whatsapp_share
pdf/        invoice_generator.py  (ReportLab canvas, A4 cash-memo)
cloud/      drive_sync.py         (OAuth + Sync_Queue + background thread)
config.py   paths, PyInstaller awareness, AppData, legacy-DB migration
```

**Pattern:** clean layered MVC. UI pages call repo functions directly; repos own *all* SQL; `utils` holds pure helpers. No ORM, no DI, no event bus. Pages are instantiated lazily and refreshed via `refresh()` hooks. For a ~6 kLOC desktop app this is the right amount of structure — easy to follow, nothing over-engineered.

**Storage layout:** `<bills base>/<Customer - phone>/<YYYY>/<BillNo - Customer>.pdf`. The base is user-configurable in Settings, and the documented trick is to point it at a Google Drive Desktop folder for free file sync. PDF lookup scans both the new per-customer layout and the legacy `base/<year>/` layout.

---

## 3. Data model

8 tables: `Users` (single bcrypt hash), `Customers`, `Services`, `Bills`, `Bill_Items`, `Payments`, `Sync_Queue`, `Settings`.

Connections set `foreign_keys=ON`, `journal_mode=WAL`, `synchronous=NORMAL`. Six indexes are created idempotently at startup. Migrations are column-presence checks in `db.py` (`bill_address`, `tax_percent`, `tax_amount`, `discount_amount` were added this way) — workable at this scale, though there is no schema-version table, so migrations can only ever be additive and order-independent.

---

## 4. Business logic — verified by execution ✅

```
subtotal = Σ qty × rate
taxable  = max(0, subtotal − discount)
tax      = taxable × gst% / 100
total    = taxable + tax
due      = total − advance
status   = Due (adv ≤ 0) | Paid (adv ≥ total) | Partial
```

I ran the real repo functions against a temp DB:

| Test | Result |
|---|---|
| 2×₹500, −₹100 disc, 18% GST, ₹200 adv | subtotal 1000 → tax 162 → **total 1062**, due 862, `Partial` ✅ |
| Bill numbering past 999 (forced `2026-999`) | next = **`2026-1000`** ✅ numeric MAX, not lexical |
| Edit bill preserving GST/discount | total stays **1062**, tax **162** ✅ (the old v1.0 bug is genuinely fixed) |
| Advance > total on create | rejected: *"Advance (₹500.00) cannot exceed Total (₹100.00)"* ✅ |
| Overpayment on collect | rejected: *"Payment is more than due amount."* ✅ |

The identical math is implemented in `bills_repo.create_bill`, `bills_manage_repo.update_bill` and mirrored live in both UIs. Writes are wrapped in `BEGIN IMMEDIATE` with rollback. **The money math is correct and consistently applied** — the most important thing in a billing app.

### PDF pagination — verified ✅

The bundled analysis claimed a fixed "last page silently drops an item" bug. I generated real PDFs and extracted the text with `pypdf` for item counts 1, 20, 21, 22, 23, 43, 44, 45, 66 and 100:

```
n=  1 pages=1 missing=0  totals_ok=True
n= 22 pages=2 missing=0  totals_ok=True
n= 44 pages=3 missing=0  totals_ok=True
n=100 pages=6 missing=0  totals_ok=True
```

**Zero items dropped at any count, GRAND TOTAL present on every last page.** The shared `_page_geometry` / `_totals_metrics` fix is real and holds at the boundary cases.

---

## 5. Audit of the bundled ANALYSIS.md claims

| Claim | Verdict |
|---|---|
| `13.5` font `TclError` blanking the app fixed | ✅ no non-integer font sizes remain |
| Dead `from assets import app_icon_path` removed | ✅ gone from `main.py` |
| `sync_repo.mark_failed()` added for stuck queue rows | ✅ present |
| `is_online()` moved off the UI thread | ✅ daemon thread + `after()` in `dashboard.py` |
| Invoice pagination / totals overflow fixed | ✅ verified by PDF extraction above |
| `_title()` preserves acronyms via `smart_title` | ✅ delegates correctly |
| "UTF-8 BOMs stripped from three repo files" | ❌ **overstated** — BOMs remain in `database/dues_repo.py`, `database/lookups_repo.py`, `utils/auth.py`, `utils/normalize_names.py` |
| `get_top_customers()` is dead code | ✅ still unreferenced by any UI |

So the prior document is largely honest, with one inaccurate hygiene claim. Its self-assessed grade of **A−** is defensible for the code, but it ignores the repo-packaging problem entirely.

---

## 6. Open issues I confirmed by running the code

### 🔴 1. Dashboard and reports under-report actual collections
`get_dashboard_stats()` sums `Bills.advance_paid` filtered by **`Bills.created_at`**, not by `Payments.paid_at`. Reproduced: a bill dated 2026-07-01, fully paid ₹1000 **today**, yields

```
today_earnings: 0.0     month_earnings: 0.0     active_customers: 0
```

₹1000 was collected today and the dashboard shows ₹0. For a contractor chasing dues, "Today's Collection" is *the* number they look at, and it is wrong whenever payment date ≠ bill date. The same flaw affects daily/monthly "Received" in Reports. **Fix:** join `Payments` for collection metrics; keep bill-based sums as "revenue billed".

### 🔴 2. Editing a bill silently destroys payment history consistency
`update_bill` writes `advance_paid` directly and never reconciles `Payments`. Reproduced: bill with a recorded ₹1000 payment, edited → `advance_paid = 0` while `SUM(Payments) = 1000`. The ledger and the header now disagree permanently, and the customer's due is overstated by ₹1000. **Fix:** recompute `advance_paid` from `Payments`, or write a correction row and forbid direct advance edits on bills that have payments.

### 🟠 3. No DB-level uniqueness on phone / service name
Phone uniqueness is enforced only in Python. Reproduced: a direct `INSERT` of a duplicate `9876543210` **succeeded** — only a non-unique `idx_customers_phone` exists. Any path that bypasses the repo (the `normalize_names.py` script, a restored backup, manual DB edit) can create duplicates that then confuse customer search and dues. **Fix:** `CREATE UNIQUE INDEX` on `Customers.phone` and on `LOWER(Services.service_name)`, after de-duplicating existing rows.

### 🟠 4. `payment_mode` is overwritten by the latest payment
A Cash bill later settled by UPI is relabelled `UPI` wholesale. Original mode survives only implicitly in `Payments`.

### 🟡 5. Hygiene
- **No tests at all.** `requirements-dev.txt` lists pytest/black/ruff; there is no `tests/` dir and no CI. The repo layer is pure functions over SQLite — it is *trivially* testable, and my throwaway scripts above are essentially the missing test suite.
- `project_code.html` + `project_code.txt` + `project_code_clean.pdf` (~900 KB of concatenated source dumps) are committed inside the zip.
- BOMs in 4 files; `get_top_customers()`, `config.backup_db()`, `vacuum_db()` dead; `assets/logo_right.png` unused.
- `config.py` does filesystem work at **import time**, which makes testing awkward (I had to override `HOME` before importing).
- Bare `except:` in font registration, date parsing and PDF open swallow real errors.
- No password recovery; minimum password length is 4 characters.
- Drive OAuth uses the **full `drive` scope** and stores `token.json` next to the executable rather than in AppData.

---

## 7. Strengths

- **Correct, consistently applied money math** across create / edit / collect, with matching live UI validation (red borders for discount > subtotal, advance > total).
- **Transaction discipline** — `BEGIN IMMEDIATE` + rollback on every multi-statement write.
- **Genuinely professional invoice PDF**: logo, CGST/SGST split, multi-page pagination that I verified holds to 100 items, Roboto embedding with a Helvetica/`Rs.` fallback for the ₹ glyph.
- **Resilient file handling** — sanitized paths, legacy-layout scanning, regenerate-PDF-if-missing.
- **India-specific UX done right**: WhatsApp deep-link share, DD-MM-YYYY dates, UPI mode, 25/50/75/100% partial-payment buttons, 6–9 mobile prefix validation, `smart_title` that preserves MSEB/LED/UPI.
- **Complete deployment story**: PyInstaller-aware paths, AppData separation, legacy DB migration, rotating logs, Inno Setup script, pinned `requirements-lock.txt`.
- Evidence of a **disciplined hardening pass** — the v1.0 critical bugs are really fixed, not just claimed.

---

## 8. Recommended roadmap

1. **Extract the zip and commit the source tree** — unblocks all code review.
2. **Fix collection metrics** to read from `Payments` (issue 1) — user-visible wrong numbers.
3. **Fix advance/Payments divergence on edit** (issue 2) — silent data corruption.
4. **Add `pytest` for the repo layer** — totals math, numbering past 999, overpay rejection, uniqueness. Half a day's work; my verification scripts are the starting point.
5. Add UNIQUE indexes on phone and service name.
6. Preserve original payment mode; strip BOMs and dead code; drop the `project_code.*` dumps.
7. Move the Drive token into AppData and narrow the OAuth scope to `drive.file`.
8. Add a documented password-reset path.

---

## 9. Overall assessment

A **well-built, production-grade desktop billing tool** that is clearly the product of real iteration rather than a one-shot generation. The layering is coherent, the financial arithmetic is correct and defended by validation at both the UI and repo levels, and the PDF engine is better than most apps of this size. I found nothing that blocks day-to-day use.

The gaps are of two kinds. **Correctness:** two real reporting/ledger bugs (items 1 and 2) that I reproduced — both are wrong-numbers-in-front-of-the-user problems, and both are a few hours of work. **Engineering process:** shipping the entire codebase as a zip blob with zero automated tests is the actual risk to this project's future, more than any individual bug in it.

**Grade: A− on the code, C on the repository.** Fix the two ledger bugs and un-zip the source with a test suite, and this is comfortably an A.
