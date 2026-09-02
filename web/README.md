# Laxmi Electricals Billing — Mobile Web Edition

Runs the **same billing app in any mobile browser**. Same logic, same database,
same PDF invoices as the Windows desktop app.

## Why it's identical to the desktop

This web layer contains **no business rules of its own**. Every calculation,
validation and PDF is delegated to the exact modules the desktop app uses:

| Concern | Shared module |
|---|---|
| Totals, GST, bill numbering | `database/bills_repo.create_bill` |
| Edit / delete bills | `database/bills_manage_repo` |
| Customers + phone uniqueness | `database/customers_repo` |
| Services catalog | `database/services_repo` |
| Payment collection | `database/dues_repo.receive_payment` |
| Dashboard / reports | `database/dashboard_repo`, `reports_repo` |
| **Invoice PDF** | `pdf/invoice_generator.generate_invoice_pdf` |
| Login, dates, formatting | `utils/auth`, `utils/date_utils`, `utils/formatting` |

A bill created on a phone is **byte-for-byte the same PDF** as one created on the
desktop, and both read and write the same `app.db`. Fix a rule once, both fix.

## Run it

```bash
pip install -r requirements.txt -r requirements-web.txt
python run_web.py
```

It prints a LAN address like `http://192.168.1.5:8000`. Open that on any phone
on the same Wi-Fi. First visit asks you to create the admin password (or use the
existing desktop password — it's the same `Users` table).

### Add to home screen
In Chrome/Safari choose **Add to Home Screen** to get a full-screen, app-like icon.

## Screens

- **Home** — today's collection, month revenue, pending dues, customers, recent bills
- **Bills** — searchable history, tap for detail, PDF, WhatsApp, edit, delete
- **New Bill** (centre + button) — customer picker & quick-add, service autocomplete
  with default-price fill, live totals, GST chips (5/12/18), advance % chips
- **Dues** — outstanding list, filter by customer, 25/50/75/100% collect
- **More** — Customers, Services, Reports (daily/monthly + CSV), Settings

## Mobile UX notes

- Bottom tab bar with a raised "New Bill" action — reachable one-handed
- All inputs ≥46px tall and 16px font so **iOS never zooms on focus**
- `inputmode="numeric"/"decimal"` brings up number pads for phone/qty/rate
- Bottom-sheet modals, safe-area insets for notched phones
- Live validation mirrors the repo errors (discount > subtotal, advance > total)
  and disables submit before a bad request is ever sent

## Deploying beyond the LAN

The dev server is fine for a shop's own Wi-Fi. To expose it publicly:

1. Set a strong secret: `export LAXMI_SECRET="<random-string>"`
2. Put it behind HTTPS (Caddy/nginx) — session cookies and passwords in clear
   text over the internet are not acceptable.
3. Consider `--workers 2`; SQLite WAL handles a couple of workers for this load.
