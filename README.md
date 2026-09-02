# Laxmi Electricals Billing — Professional Edition v1.1

Desktop billing application built with Python + CustomTkinter + SQLite + ReportLab — designed for Indian electrical contractors.

**What’s New in v1.1 (Perfect Edition):**
- ✅ **Fixed critical bug:** Editing bills now preserves GST & Discount correctly (total recalculation fixed)
- ✅ **Bill number generation fixed:** Numeric MAX instead of lexical sort — works beyond 999 bills/year
- ✅ **Professional UI overhaul:** All pages redesigned with modern cards, icons, hover states, centered theme from `ui/theme.py`
- ✅ **Better validation:** Unique phone check, duplicate service guard, discount ≤ subtotal, advance ≤ total, Indian mobile starts with 6-9
- ✅ **Edit Bill supports GST/Discount/Address:** Full editing of taxable amount, CGST/SGST split
- ✅ **Cross-platform PDF open:** `os.startfile` replaced with platform-aware `subprocess` + fallback
- ✅ **Robust backups:** SQLite backup API with WAL mode, rotating logs (2MB), backup stats
- ✅ **Drive sync hardening:** Cache invalidation if folder deleted, escaped queries, better error handling
- ✅ **Improved autocomplete:** Larger popup, keyboard nav, screen-edge handling
- ✅ **WhatsApp + Explorer reveal cross-platform**
- ✅ **Performance indexes added** for Bills, Customers, Bill_Items

## Features
- **Customers Master:** Name (smart Title Case), 10-digit phone validation, address, bill count, due amount
- **Services Master:** Service name + default price, usage count
- **Create Bill:**
  - Search customer (name/phone) + Quick Add
  - Custom site address override per bill
  - Service autocomplete with default price fill
  - New service detection → save to catalog prompt
  - Qty/Rate/Amount live, Discount ₹, GST %, Advance ₹, Payment Mode
  - Live validation (red border if discount > subtotal etc)
  - Date picker DD-MM-YYYY custom date support, bill number YYYY-NNN per year
  - Generates professional PDF with logo, GST split CGST/SGST, multi-page
- **Bills History:** 120 recent, search bill/customer/phone, Open PDF auto-regenerates if missing, WhatsApp share with prefilled message + Explorer reveal, Edit (full GST/Discount), Delete (removes PDFs)
- **Pending Dues:** Filter by customer, search, quick % buttons (25/50/75/100) for partial payment, collect payment → updates PDF
- **Dashboard:** Today’s Collection, Monthly Revenue, Pending Amount, Active Customers, growth %, Quick Actions, Alerts, Recent Bills
- **Reports:** Daily (YYYY-MM-DD) + Monthly (Year/Month) summary Total/Received/Due/Bills count + table + CSV export
- **Settings:**
  - Business profile (name/phone/address on invoice)
  - Appearance light/dark persisted
  - Bills folder chooser (tip: pick Google Drive My Drive folder)
  - Backup: create local backup (SQLite backup API), cleanup old, open folder, stats
  - Security: change password with validation
  - About + open data folder

## Tech Stack
- Python 3.10+
- CustomTkinter 5.2.2 (modern UI)
- SQLite with WAL mode + indexes
- ReportLab 4.4.10 (PDF)
- Google Drive API (optional cloud backup via queue)
- bcrypt (password hashing)
- Pillow (images)

## Setup (Dev)
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
python main.py
```

## Build (PyInstaller + Inno Setup)
```bash
# Install pyinstaller
pip install pyinstaller
pyinstaller --noconfirm --windowed --name LaxmiElectricalsBilling --icon assets/app.ico --add-data "assets;assets" --add-data "database/schema.sql;database" main.py

# Installer exe requires Inno Setup 6
# Compile installer/LaxmiElectricalsBilling.iss
```

## Storage Locations
- **Windows:** `%APPDATA%\LaxmiElectricalsBilling\`
  - DB: `app.db`
  - Bills: `bills\Customer - Phone\YYYY\BillNo - Name.pdf`
  - Backups: `backups\laxmi_billing_backup_*.db`
  - Logs: `logs\app.log` (rotating 2MB x3)
  - Exports: `exports\`
- **Linux/Mac:** `~/.laxmi_billing/` (fallback)
- PDF folder can be changed in Settings (e.g., `G:\My Drive\Laxmi Bills`)

## Business Logic
```
subtotal = Σ qty*rate
taxable = max(0, subtotal - discount)
tax = taxable * gst% /100
total = taxable + tax
due = total - advance
status = Due if advance<=0 else Paid if advance>=total else Partial
Bill No = YYYY-NNN where NNN = MAX(seq for year)+1 (numeric, not lexical)
```

## Security
- Password hashed with bcrypt, single admin user
- Token + credentials ignored via .gitignore — never commit `cloud/token.json`, `cloud/credentials.json`
- SQLite DB plaintext in AppData (desktop standard) — use Windows BitLocker or backup encryption if needed
- Phone uniqueness enforced in code, service name case-insensitive unique
- Path traversal protected via sanitization of invalid chars `<>:"/\|?*`

## Known Limitations / Future
- Single-user desktop, not multi-user network
- No password recovery — delete `%APPDATA%\LaxmiElectricalsBilling\app.db` Users table manually if forgotten
- Drive scope is full `drive` (to search root folder) — could be narrowed to `drive.file`
- No automated tests yet — add pytest for repo logic

## Credits
Built for Laxmi Electricals, Pune. By Team DuoBits. UI polished to professional perfect in v1.1.
