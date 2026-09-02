from datetime import datetime
from database.db import get_connection

def _now():
    return datetime.now().isoformat(timespec="seconds")

def _compute_status(total: float, advance: float) -> str:
    if advance <= 0:
        return "Due"
    if advance >= total:
        return "Paid"
    return "Partial"

def create_bill(customer_id: int, items: list, advance_paid: float, payment_mode: str, 
                bill_address: str = "", custom_date: str = None, 
                tax_percent: float = 0, discount_amount: float = 0):
    """
    custom_date: ISO format string "YYYY-MM-DDTHH:MM:SS". If None, uses current time.
    """
    if not customer_id:
        raise ValueError("Customer is required.")
    if not items:
        raise ValueError("Add at least one service item.")
    if payment_mode not in ("Cash", "UPI", "Bank Transfer"):
        raise ValueError("Invalid payment mode.")

    clean_items = []
    subtotal = 0.0

    for it in items:
        service_name = (it.get("service_name") or "").strip()
        if not service_name:
            raise ValueError("Service name cannot be empty.")

        try:
            qty = float(it.get("qty", 0))
            rate = float(it.get("rate", 0))
        except:
            raise ValueError("Qty and Rate must be numbers.")

        if qty <= 0:
            raise ValueError("Qty must be greater than 0.")
        if rate < 0:
            raise ValueError("Rate cannot be negative.")

        amount = qty * rate
        subtotal += amount

        clean_items.append({
            "service_name": service_name,
            "qty": qty,
            "rate": rate,
            "amount": amount
        })

    try:
        advance = float(advance_paid or 0)
        tax_percent = float(tax_percent or 0)
        discount = float(discount_amount or 0)
    except:
        raise ValueError("Advance, Tax, and Discount must be numbers.")

    if advance < 0 or tax_percent < 0 or discount < 0:
        raise ValueError("Values cannot be negative.")
    if tax_percent > 100:
        raise ValueError("GST cannot be more than 100%.")
    if discount > subtotal:
        raise ValueError(f"Discount (₹{discount:.2f}) cannot exceed Subtotal (₹{subtotal:.2f}).")
    
    # Calculation Logic
    taxable_amount = subtotal - discount
    if taxable_amount < 0:
        taxable_amount = 0
    
    tax_amount = (taxable_amount * tax_percent) / 100.0
    total_amount = taxable_amount + tax_amount
    
    if advance > total_amount:
        raise ValueError(f"Advance (₹{advance:.2f}) cannot exceed Total (₹{total_amount:.2f}).")
    
    due_amount = total_amount - advance
    status = _compute_status(total_amount, advance)

    bill_address = (bill_address or "").strip()

    # Date & Year logic
    if custom_date:
        created_at = custom_date
        try:
            # Parse ISO to get the correct year for the Bill Number
            dt_obj = datetime.fromisoformat(created_at)
            year = dt_obj.year
        except:
            # Fallback if format is weird
            year = datetime.now().year
    else:
        created_at = _now()
        year = datetime.now().year

    con = get_connection()
    try:
        con.execute("BEGIN IMMEDIATE;")

        # Robust numeric max per year (fixes lex sorting after 999 and 2024-100 vs 2024-99 issues)
        row = con.execute(
            """
            SELECT COALESCE(MAX(CAST(substr(bill_number, instr(bill_number, '-')+1) AS INTEGER)), 0) AS max_seq
            FROM Bills
            WHERE bill_number LIKE ?;
            """,
            (f"{year}-%",)
        ).fetchone()

        last_seq = 0
        if row:
            try:
                last_seq = int(row["max_seq"] or 0)
            except:
                last_seq = 0

        bill_number = f"{year}-{last_seq + 1:03d}"

        cur = con.execute(
            """
            INSERT INTO Bills(
                bill_number, customer_id, subtotal, advance_paid, due_amount,
                total_amount, payment_mode, status, created_at, updated_at,
                bill_address, tax_percent, tax_amount, discount_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?);
            """,
            (
                bill_number, customer_id, subtotal, advance, due_amount,
                total_amount, payment_mode, status, created_at,
                bill_address, tax_percent, tax_amount, discount
            )
        )
        bill_id = cur.lastrowid

        for it in clean_items:
            con.execute(
                """
                INSERT INTO Bill_Items(bill_id, service_name, qty, rate, amount)
                VALUES (?, ?, ?, ?, ?);
                """,
                (bill_id, it["service_name"], it["qty"], it["rate"], it["amount"])
            )

        con.commit()
        return bill_id, bill_number
    except:
        con.rollback()
        raise
    finally:
        con.close()

def get_bill_bundle(bill_id: int):
    con = get_connection()
    try:
        bill = con.execute("SELECT * FROM Bills WHERE id=?;", (bill_id,)).fetchone()
        if not bill:
            raise ValueError("Bill not found.")

        customer = con.execute("SELECT * FROM Customers WHERE id=?;", (bill["customer_id"],)).fetchone()
        items = con.execute("SELECT * FROM Bill_Items WHERE bill_id=? ORDER BY id;", (bill_id,)).fetchall()

        return {
            "bill": dict(bill),
            "customer": dict(customer) if customer else None,
            "items": [dict(i) for i in items],
        }
    finally:
        con.close()
