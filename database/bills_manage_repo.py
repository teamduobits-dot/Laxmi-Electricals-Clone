from datetime import datetime
import sqlite3
from database.db import get_connection

def _now():
    return datetime.now().isoformat(timespec="seconds")

def _compute_status(total: float, advance: float) -> str:
    if advance <= 0:
        return "Due"
    if advance >= total:
        return "Paid"
    return "Partial"

def list_bills(search: str = "", limit: int = 50):
    s = (search or "").strip()
    con = get_connection()
    try:
        if not s:
            rows = con.execute(
                """
                SELECT b.id, b.bill_number, b.created_at, c.name AS customer_name,
                       b.total_amount, b.advance_paid, b.due_amount, b.status, b.payment_mode,
                       b.discount_amount, b.tax_percent, b.tax_amount, b.subtotal
                FROM Bills b
                JOIN Customers c ON c.id = b.customer_id
                ORDER BY b.id DESC
                LIMIT ?;
                """,
                (int(limit),)
            ).fetchall()
        else:
            like = f"%{s}%"
            rows = con.execute(
                """
                SELECT b.id, b.bill_number, b.created_at, c.name AS customer_name,
                       b.total_amount, b.advance_paid, b.due_amount, b.status, b.payment_mode,
                       b.discount_amount, b.tax_percent, b.tax_amount, b.subtotal
                FROM Bills b
                JOIN Customers c ON c.id = b.customer_id
                WHERE b.bill_number LIKE ? OR c.name LIKE ? OR c.phone LIKE ?
                ORDER BY b.id DESC
                LIMIT ?;
                """,
                (like, like, like, int(limit))
            ).fetchall()

        return [dict(r) for r in rows]
    finally:
        con.close()

def update_bill(bill_id: int, customer_id: int, items: list, advance_paid: float, payment_mode: str,
                tax_percent: float = 0, discount_amount: float = 0, bill_address: str | None = None):
    if not bill_id:
        raise ValueError("Bill id missing.")
    if not customer_id:
        raise ValueError("Customer is required.")
    if not items:
        raise ValueError("At least one item is required.")
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
            raise ValueError("Qty/Rate must be numbers.")

        if qty <= 0:
            raise ValueError("Qty must be > 0.")
        if rate < 0:
            raise ValueError("Rate cannot be negative.")

        amount = qty * rate
        subtotal += amount

        clean_items.append({
            "service_name": service_name,
            "qty": qty,
            "rate": rate,
            "amount": amount,
        })

    try:
        advance = float(advance_paid or 0)
        t_percent = float(tax_percent or 0)
        discount = float(discount_amount or 0)
    except:
        raise ValueError("Advance, Tax, Discount must be numbers.")

    if advance < 0:
        raise ValueError("Advance cannot be negative.")
    if t_percent < 0:
        raise ValueError("GST cannot be negative.")
    if discount < 0:
        raise ValueError("Discount cannot be negative.")
    if discount > subtotal:
        raise ValueError(f"Discount (₹{discount:.2f}) cannot be greater than Subtotal (₹{subtotal:.2f}).")

    taxable = subtotal - discount
    if taxable < 0:
        taxable = 0
    tax_amount = (taxable * t_percent) / 100.0
    total_amount = taxable + tax_amount

    if advance > total_amount:
        raise ValueError(f"Advance (₹{advance:.2f}) cannot be greater than Total (₹{total_amount:.2f}).")

    due_amount = total_amount - advance
    if due_amount < 0:
        due_amount = 0.0
    status = _compute_status(total_amount, advance)

    con = get_connection()
    try:
        con.execute("BEGIN IMMEDIATE;")

        # Check if bill_address column update needed
        if bill_address is not None:
            con.execute(
                """
                UPDATE Bills
                SET customer_id=?,
                    subtotal=?,
                    discount_amount=?,
                    tax_percent=?,
                    tax_amount=?,
                    advance_paid=?,
                    due_amount=?,
                    total_amount=?,
                    payment_mode=?,
                    status=?,
                    bill_address=?,
                    updated_at=?
                WHERE id=?;
                """,
                (customer_id, subtotal, discount, t_percent, tax_amount,
                 advance, due_amount, total_amount, payment_mode, status,
                 bill_address.strip(), _now(), bill_id)
            )
        else:
            con.execute(
                """
                UPDATE Bills
                SET customer_id=?,
                    subtotal=?,
                    discount_amount=?,
                    tax_percent=?,
                    tax_amount=?,
                    advance_paid=?,
                    due_amount=?,
                    total_amount=?,
                    payment_mode=?,
                    status=?,
                    updated_at=?
                WHERE id=?;
                """,
                (customer_id, subtotal, discount, t_percent, tax_amount,
                 advance, due_amount, total_amount, payment_mode, status, _now(), bill_id)
            )

        # replace bill items
        con.execute("DELETE FROM Bill_Items WHERE bill_id=?;", (bill_id,))
        for it in clean_items:
            con.execute(
                """
                INSERT INTO Bill_Items(bill_id, service_name, qty, rate, amount)
                VALUES (?, ?, ?, ?, ?);
                """,
                (bill_id, it["service_name"], it["qty"], it["rate"], it["amount"])
            )

        con.commit()
    except sqlite3.Error:
        con.rollback()
        raise
    finally:
        con.close()

def delete_bill(bill_id: int):
    con = get_connection()
    try:
        con.execute("DELETE FROM Bills WHERE id=?;", (bill_id,))
        con.commit()
    finally:
        con.close()
