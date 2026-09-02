# Laxmi Electricals Billing — Complete Project Analysis

**Date:** 2026-08-07 (re-analyzed against current code on branch `arena/019fdc7f-laxmi-electricals-billing`)
**Version analyzed:** 1.1.0 ("Professional Edition")
**Tech stack:** Python 3.10+, CustomTkinter 5.2.2, SQLite (WAL), ReportLab 4.4.10, Google Drive API, bcrypt, Pillow
**Size:** ~6,100 lines of Python across 36 modules + SQL schema + Inno Setup installer
**Entry point:** `main.py` → `App(ctk.CTk)`

---

## 1. What this project is

A single-user Windows desktop billing application for **Laxmi Electricals**, an electrical labour contractor in Pune. It covers the full billing lifecycle:

- Customer master (name auto-Title-Case, validated 10-digit Indian mobile, address)
- Services catalog with default prices
- Invoice creation with GST, discount, advance payment, per-bill site address, custom bill date
- Professional PDF invoices (logo, CGST/SGST split, multi-page) saved into per-customer / per-year folders
- Bill history with edit, delete, PDF regeneration, WhatsApp sharing
- Pending-dues tracking with partial payments (25/50/75/100% quick buttons) and payment history
- Dashboard (today's collection, monthly revenue, pending dues, growth %)
- Daily/monthly reports with CSV export
- Local DB backups, optional Google Drive cloud backup with offline queue
- bcrypt-hashed admin password login; light/dark theme

Distribution is PyInstaller + Inno Setup (`installer/LaxmiElectricalsBilling.iss`), installing per-user to `LocalAppData\Programs`.

---

## 2. Architecture

```
main.py (App: CTk root, logging, theme, routing)
 ├── LoginFrame            ui/login.py      (first-run password setup / login)
 └── AppShell              ui/shell.py      (sidebar + topbar + lazy page switching)
      ├── DashboardPage    ui/dashboard.py
      ├── CustomersPage    ui/customers.py  (+CustomerForm, CustomerBillsModal, PaymentForm)
      ├── ServicesPage     ui/services.py
      ├── BillingPage      ui/billing.py    (create bill; biggest module, 687 LOC)
      ├── BillsPage        ui/bills.py      (history; +BillEditForm)
      ├── DuesPage         ui/dues.py       (+PaymentForm)
      ├── ReportsPage      ui/reports.py
      └── SettingsPage     ui/settings.py   (+ChangePasswordForm)

Data layer (no ORM; raw sqlite3 with Row factory):
 database/db.py              connection + migrations + indexes
 database/schema.sql         8 tables
 database/*_repo.py          one repo per domain (bills, bills_manage, customers,
                             services, dues, reports, dashboard, lookups, settings,
                             sync, customer_bills)

Cross-cutting:
 config.py                   paths, constants, AppData folders, legacy-DB migration
 utils/                      auth (bcrypt), storage (PDF paths), validators,
                             formatting (smart_title), date_utils, backup,
                             whatsapp_share, normalize_names (one-off script)
 pdf/invoice_generator.py    ReportLab canvas invoice
 cloud/drive_sync.py         Google Drive upload + Sync_Queue + background thread
```

**Pattern:** simple layered MVC — UI pages call repo functions directly; repos own all SQL; `utils` holds pure helpers. No dependency injection, no event bus; pages are created lazily and refreshed via `refresh()`/`load_lookups()` hooks when revisited.

**Storage layout** (`config.py`):
- Data: `%APPDATA%\LaxmiElectricalsBilling\` (`app.db`, `backups\`, `logs\` rotating 2MB×3, `exports\`, default `bills\`); Linux/macOS fallback `~/.laxmi_billing/`
- Invoices: `<bills base>/<Customer Name - phone>/<YYYY>/<BillNo - Customer>.pdf`; the base folder is changeable in Settings (tip: point it at Google Drive Desktop's "My Drive" for free file-level sync)
- Legacy migration: old `app.db` in the program dir is copied into AppData on first run; PDF lookup scans both the legacy `base/<year>/` layout and the new per-customer layout

---

## 3. Database design (`database/schema.sql` + migrations in `db.py`)

| Table | Purpose | Notes |
|---|---|---|
| `Users` | single admin | only `password_hash` (bcrypt) |
| `Customers` | master | no UNIQUE constraint on phone (uniqueness enforced in app code) |
| `Services` | catalog | denormalized copies of names kept in `Bill_Items` for history |
| `Bills` | invoice header | `bill_number UNIQUE` (`YYYY-NNN`), FK to customer `ON DELETE RESTRICT`; `bill_address`, `tax_percent`, `tax_amount`, `discount_amount` added via column-existence migrations in `db.py` |
| `Bill_Items` | line items | FK `ON DELETE CASCADE` |
| `Payments` | payment history | one row per collection; FK cascade |
| `Sync_Queue` | Drive upload queue | `PENDING`/`SYNCED` per bill+file |
| `Settings` | key/value | theme, business profile, bills dir, Drive folder IDs |

Connections enable `foreign_keys`, `journal_mode=WAL`, `synchronous=NORMAL`. Six performance indexes are created idempotently at startup (bills by customer/created/number/due, customers by phone, items by bill). Migration strategy is column-presence checks — fine at this scale; there is no schema version table.

---

## 4. Core business logic (verified in current code)

**Totals** (identical in create `bills_repo.create_bill`, edit `bills_manage_repo.update_bill`, and both UIs):

```
subtotal = Σ qty × rate
taxable  = max(0, subtotal − discount)
tax      = taxable × gst% / 100
total    = taxable + tax
due      = total − advance
status   = Due (advance ≤ 0) | Paid (advance ≥ total) | Partial
```

**Validation** (repo-level, with matching UI red-border feedback):
- qty > 0, rate ≥ 0, payment mode ∈ {Cash, UPI, Bank Transfer}
- discount ≥ 0 and **discount ≤ subtotal** (error otherwise)
- GST 0–100, advance ≥ 0 and **advance ≤ total**
- customer phone: exactly 10 digits, must start with 6–9, **unique across customers** (code check, add and edit)
- service names unique case-insensitively; service price ≤ 10,00,000

**Bill numbering:** `YYYY-NNN` where the sequence is `MAX(CAST(substr(bill_number, after '-') AS INTEGER))` per year — numeric, so it works past 999 bills/year. Wrapped in `BEGIN IMMEDIATE`, so concurrent creation is serialized by SQLite. A user-picked bill date (DD-MM-YYYY in the UI) determines the year of the bill number while `created_at` keeps the current time for sorting.

**Payments:** `receive_payment` adds to `advance_paid`, rejects overpayment (`new advance > total`), writes a `Payments` row, and the UI regenerates the PDF afterwards. Editing a bill replaces items wholesale and rewrites header totals including tax/discount/address; the PDF is regenerated on save.

**PDF lifecycle:** PDFs are generated after create/edit/payment. "Open PDF" falls back to regenerating from the DB when the file is missing. Delete removes the DB row (cascades items/payments) **and** every matching PDF in both folder layouts.

---

## 5. Module-by-module notes

### `config.py`
Clean PyInstaller awareness (`PROGRAM_DIR` vs `_MEIPASS` resource dir), cross-platform AppData selection, legacy DB migration. ⚠ Runs `ensure_app_folders()`/`migrate_old_db_if_needed()` **at import time** (import side effects). `backup_db()` here is unused (the real backup lives in `utils/backup.py`). Business defaults are hardcoded (including a placeholder phone `9999999999`) but overridable via Settings.

### `database/db.py`
Solid. `_column_exists` uses `PRAGMA table_info({table})` with an f-string — safe today since table names are internal constants, but worth noting. `vacuum_db()` exists but is never called from the UI.

### Repos
- **bills_repo.py** — create path + `get_bill_bundle`. Transactional (`BEGIN IMMEDIATE`, rollback), thorough validation.
- **bills_manage_repo.py** — list (search by bill no/customer/phone, limit 120 from UI), full GST/discount-aware `update_bill` (with optional `bill_address` handling), `delete_bill`. ✅ The v1.0 "edit strips GST" bug is **fixed**.
- **customers_repo.py** — CRUD with smart-title names, phone validation + uniqueness check, delete guarded by FK RESTRICT with friendly error, paginated search with per-customer bill count / total billed / total due subqueries.
- **services_repo.py** — CRUD, case-insensitive duplicate guard, usage count against `Bill_Items`.
- **dues_repo.py** — due-bill listing with customer filter + search; transactional `receive_payment`. ⚠ Overwrites the bill's `payment_mode` with the latest payment's mode.
- **reports_repo.py** — daily (`date(created_at)`) and monthly (`strftime('%Y-%m')`) summaries + bill lists (now including subtotal/discount/tax columns) + `available_years`.
- **dashboard_repo.py** — today/month/prev-month collections, pending dues, active customers, growth %, recent bills, plus `get_top_customers` (**currently unused by any UI page**).
- **lookups / settings / sync / customer_bills** — small, correct key-value and queue helpers. ⚠ `sync_repo.py`, `settings_repo.py`, `customer_bills_repo.py` start with a UTF-8 BOM (`\ufeff`) — Python tolerates it, but linters/tools may trip on it.

### `utils/`
- **auth.py** — bcrypt hashing; `set_admin_password` does DELETE-then-INSERT (single user); change-password validates current password, min length 4.
- **storage.py** — the PDF path engine: sanitized customer folders (`<>:"/\|?*` stripped, trailing dots/spaces removed, smart_title applied), legacy+new folder scanning, newest-first dedupe, delete-all-matches, per-customer PDF walk. Renaming a customer orphans the old folder (old PDFs still findable via scan; new PDFs go to the new folder) — acceptable, documented behavior.
- **validators.py / formatting.py / date_utils.py** — phone cleaning (keeps last 10 digits), Indian-mobile check, live entry sanitizers, `smart_title` (preserves UPI/GST/MSEB/LED etc.), multi-format date parsing, DD-MM-YYYY↔ISO conversion.
- **backup.py** — uses the SQLite online-backup API with file-copy fallback and retries, list/cleanup/stats.
- **whatsapp_share.py** — `wa.me/91XXXXXXXXXX?text=…` deep link + reveal-in-explorer; ✅ now platform-aware (Windows `start`, macOS `open`, Linux `xdg-open`).
- **normalize_names.py** — standalone one-off script (smart_title sweep over Customers/Services/Bill_Items); builds its own `sys.path`; f-string SQL with internal-only identifiers.

### `pdf/invoice_generator.py` (396 LOC)
ReportLab canvas, A4, red-bordered Indian "Cash Memo" style: logo, centered business name/tagline/address, customer/bill info block, items table with dashed row guides, bottom band with dynamic totals box (Subtotal, Discount, CGST/SGST split, Advance, Balance Due, GRAND TOTAL) and signature block. Roboto TTF registration with Helvetica/`Rs.` fallback (Roboto gives ₹ glyph). Multi-page pagination with totals only on the last page. See §7 for two rendering edge cases found during this review.

### `cloud/drive_sync.py`
Full-Drive-scope OAuth (`credentials.json`/`token.json` in `cloud/`, both git-ignored). Token refresh with re-auth fallback, root/year folder resolution with **cached folder-ID validation and cache invalidation** (✅ hardened since v1.0), upload-or-queue with resumable `MediaFileUpload`, background daemon thread with a lock to prevent double runs.

### `ui/`
- **theme.py** is the single source of truth for (light, dark) color tuples; all pages now consume it (v1.0 duplication largely resolved).
- **shell.py** — dark sidebar with unicode icons, active-state highlighting, logout; topbar with theme toggle; lazy page instantiation.
- **billing.py** (687 LOC, the heart) — customer search + pinned selection + Quick Add modal; per-bill custom address modal; service rows with custom `SuggestionPopup` autocomplete, new-service detection with "save to catalog" prompt; live recalc with visual validation (red borders for discount > subtotal / advance > total); DD-MM-YYYY date entry; generate → PDF → auto-open (platform-aware); form reset keeps the customer pinned.
- **bills.py** — history table (120 rows), Open PDF with regenerate fallback, WhatsApp share (deep link + file reveal + instructions), full edit form (customer, items, discount, GST, advance, address, mode) with PDF regeneration, delete with PDF cleanup. ⚠ Edit items use an OptionMenu (no free-typed new services), unlike the create page's autocomplete — an inconsistency, not a bug.
- **customers.py / services.py / dues.py** — standard CRUD pages with selection highlighting, modals, and bill-history drill-through per customer (with inline payment collection).
- **dashboard.py** — 4 stat cards, quick actions, dues alert, recent bills; online badge pings 8.8.8.8:53 with 0.8 s timeout **on the UI thread**.
- **reports.py** — daily/monthly tab views with summary cards and CSV export via `DictWriter` (headers derived from the query columns — includes discount/tax now).
- **settings.py** — business profile, theme, bills-folder chooser with write-test, backup (create + keep-20 cleanup + stats), change password, about/data-folder.
- **autocomplete.py** — custom borderless topmost Listbox popup with keyboard navigation, scrollbar, delayed focus-out hide.

---

## 6. Security review

| Area | Status |
|---|---|
| Password storage | ✅ bcrypt with generated salt; single-admin model |
| Password policy | ⚠ min 4 chars only; **no recovery mechanism** (documented: delete DB Users row) |
| SQL injection | ✅ all queries parameterized, except internal-only identifier interpolation (`PRAGMA table_info`, normalize script) |
| Secrets | ✅ `cloud/token.json` / `credentials.json` git-ignored; ⚠ token.json stored in plaintext next to the app |
| Drive OAuth scope | ⚠ full `drive` scope (needed to search for the root folder by name); could be narrowed with appDataFolder or stored-ID-only strategy |
| Path traversal | ✅ invoice filenames sanitized of `<>:"/\|?*` and trailing dots |
| Data at rest | ⚠ SQLite + backups unencrypted in AppData (standard for desktop apps; README suggests BitLocker) |
| Logging | ✅ rotating 2MB×3, no secrets logged |

---

## 7. Issues found in this review (current code)

### Fixed in the 2026-08-07 follow-up pass ✅

0. **Login → blank window crash (the reported bug).** `ui/shell.py` built the sidebar nav buttons with `ctk.CTkFont(size=13.5)`; Tk font sizes must be integers, so the first nav button raised `TclError: expected integer but got "-13.5"` inside `AppShell` construction — right after the login screen is cleared. Console traceback + blank window, exactly as reported. Fixed (`size=14`).
   Hardening added so this class of bug can never blank the app again: `main.show_app` now catches shell-build failures (logs + error dialog + returns to login), and `AppShell.show_page` renders an inline "page failed to load" card instead of propagating a page-construction exception.
1. **Invoice last-page item clipping — fixed & verified.** Pagination and the renderer now share one geometry source (`_page_geometry`); middle pages hold `rows_full` rows, the totals page never more than `rows_last`. Verified with pypdf text extraction: a 22-item GST+discount bill renders all 22 items (previously the 22nd silently dropped), 21- and 42-item bills paginate cleanly.
2. **Totals box overflowing the bottom band — fixed.** The bottom band now grows to fit the tallest totals box (`_totals_metrics`), keeping the box, signature and frame aligned.
3. **`main.py` dead `from assets import app_icon_path` removed.**
4. **Stuck Sync_Queue rows — fixed.** `sync_repo.mark_failed()` added; `sync_pending_uploads` marks entries whose PDF is missing as `FAILED` instead of leaving them PENDING forever.
5. **Dashboard network probe off the UI thread.** `is_online()` now runs in a daemon thread; the badge updates via `after()` (no more 0.8 s block per refresh).
6. **PDF acronym mangling — fixed.** `_title()` delegates to `smart_title`, so MSEB/LED/UPI survive on invoices.
7. **Hygiene:** UTF-8 BOMs stripped from three repo files; unused imports/variables removed across `ui/` (`ruff --select F` now fully clean).

### Previously reported (now historical)
*(Items 1–4, 9, 10 and 12 in this historical list are resolved — see the "Fixed" subsection above.)*

1. **Invoice last-page item clipping (edge case).** `rows_per_page` (=22 on A4) is computed with a 12 px bottom buffer, but the final page uses a 52 px `min_y` guard to keep items away from the totals box. If a bill's item count is an exact multiple of 22, the last page is full and the draw loop `break`s early — **the final item silently drops off the PDF**. Fix: reduce `rows_per_page` by 1–2 for the totals page, or paginate with the totals-page guard in mind.
2. **Tall totals box overflows the bottom band.** With discount + GST, the totals box has 6 rows → height ≈ 130 px, but the bottom band is only 112 px tall; the box (and signature line) extends ~30 px past the red frame into the table area. Cosmetic, but it crosses the band border.
3. **`main.py` dead import:** `from assets import app_icon_path` always fails (assets is not a package) and is swallowed by a bare `except` — remove it.
4. **Stale Sync_Queue rows forever:** in `sync_pending_uploads`, a queued PDF whose file no longer exists is skipped but never marked, so it stays PENDING permanently. Should mark as `FAILED`/`SYNCED` after N attempts.
5. **Payments/advance divergence on edit:** `update_bill` sets `advance_paid` directly without touching the `Payments` history, so after editing, header advance and Σ Payments can disagree. Consider adjusting/recording a correction payment row.
6. **Dashboard "Today's Collection" semantics:** sums `advance_paid` of bills *created* today; payments collected today against older bills (recorded in `Payments.paid_at`) are not counted. Same caveat for monthly revenue and daily/monthly "received" in reports. If "collection" should mean cash received, query the `Payments` table.

### Design / quality
7. **Phone uniqueness only in app code** — no DB `UNIQUE` index on `Customers.phone`; concurrent edits or external DB access can still create duplicates (an index exists, but not a unique one). Same for `Services.service_name`.
8. **`payment_mode` overwritten** by the latest partial payment (dues) and by edits — original mode history only survives implicitly in `Payments`.
9. **`is_online()` blocks the UI thread** up to 0.8 s per dashboard refresh.
10. **PDF `_title()` re-capitalizes service names** (`w.capitalize()`), so acronyms like "MSEB" render as "Mseb" on invoices, despite `smart_title` preserving them elsewhere.
11. **`get_top_customers()`** in dashboard_repo is dead code; `config.backup_db()` and `vacuum_db()` are unused.
12. **BOM (`\ufeff`)** at the top of `sync_repo.py`, `settings_repo.py`, `customer_bills_repo.py`.
13. **`config.py` performs filesystem work at import time** — makes testing harder.
14. **No tests.** `requirements-dev.txt` lists pytest/black/ruff but there is no `tests/` directory and no CI.
15. **Repo hygiene:** `project_code.html` / `project_code.txt` / `project_code_clean.pdf` (~900 KB) are concatenated-source artifacts committed to the repo — candidates for removal/git-ignoring; `assets/logo_right.png` is unused (only `logo_left.png` renders).
16. **Drive token location:** written next to the executable; fine for per-user installs, but worth moving into AppData alongside the DB for consistency.
17. Bare `except:` clauses in several spots (font registration, PDF open, date parsing) hide real errors; `logging.exception` would help supportability.

### What was previously broken and is now **verified fixed** ✅
- Edit-bill path preserves GST, discount, address; totals recomputed correctly (`update_bill`)
- Bill numbering uses numeric MAX per year (works beyond 999/year)
- Cross-platform PDF open / WhatsApp / Explorer reveal (`platform.system()` branches)
- Rotating log handler (2 MB × 3)
- Drive folder-ID cache validation + invalidation (`_validate_folder_id`)
- Phone uniqueness checks, case-insensitive service uniqueness, discount ≤ subtotal, advance ≤ total, Indian mobile 6–9 prefix checks
- Backup via SQLite backup API with fallback; write-test on bills-folder change

---

## 8. Strengths

- **Coherent layered structure** with small, focused modules; raw SQL kept in repos; easy to follow
- **Correct, consistently applied money math** across create/edit/collect paths with strong validation and matching UI feedback
- **Transaction discipline** (`BEGIN IMMEDIATE` + rollback) on all multi-statement writes
- **Professional invoice PDF** with GST split, multi-page support, font fallback, logo
- **Resilient file layout**: per-customer/year folders with legacy-layout scanning and regenerate-on-missing fallbacks
- **India-specific UX done right**: WhatsApp deep-link share with file reveal, ₹ formatting, DD-MM-YYYY dates, UPI payment mode, quick partial-payment percentages
- **Offline-tolerant cloud backup** via queue + background sync, with folder-ID cache invalidation
- **Deployment story complete**: PyInstaller-aware paths, AppData separation, legacy DB migration, Inno Setup script, rotating logs

## 9. Suggested roadmap

1. Fix invoice pagination for totals pages (issues 1–2) — small change, prevents silent data loss on PDFs
2. Add `pytest` coverage for the repo layer: totals math, bill numbering past 999, payment overpay rejection, phone/service uniqueness
3. Add DB-level `UNIQUE` indexes on `Customers.phone` and `Services.service_name`
4. Base "collections" metrics on the `Payments` table; keep bill-based "revenue" separate
5. Mark/expire stuck Sync_Queue entries; move Drive token into AppData; consider narrowing OAuth scope
6. Remove dead code and committed code-dump artifacts (`project_code.*`, unused functions, BOMs)
7. Add a password-recovery or reset mechanism (even a documented admin tool)
8. Small UX: run online check off the UI thread; allow free-typed services in the edit form; preserve original payment mode in history views

## 10. Overall assessment

A **production-grade, well-scoped desktop billing tool** that clearly went through a disciplined v1.0 → v1.1 hardening pass: every critical bug from the earlier review is genuinely fixed in the current code, validation is thorough, and the transaction/storage/backup handling is more robust than typical apps of this size. The remaining issues are mostly edge cases (invoice pagination, dashboard collection semantics, stuck queue rows) and hygiene (tests, dead code, repo artifacts). Nothing found blocks shipping; items 1–3 of the roadmap above would raise confidence for high-volume use.

**Grade: A−** (up from B+ in the v1.0 analysis; the edit-bill and bill-numbering fixes land it here — invoice pagination and tests are the gap to an A).
*Post-review update (same day): the login-blocking `TclError`, invoice pagination/overflow, stuck sync queue, blocking network probe, and lint hygiene items were all fixed and verified headlessly; remaining gaps to an A are automated tests and the collection-semantics/dashboard metrics notes in §7/§9.*
