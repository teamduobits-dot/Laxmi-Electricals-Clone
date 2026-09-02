from datetime import datetime
from database.db import get_connection

def _now():
    return datetime.now().isoformat(timespec="seconds")

def list_due_bills(search: str = "", customer_id: int | None = None, limit: int = 200):
    s = (search or "").strip()
    con = get_connection()
    try:
        base_sql = """
            SELECT
              b.id,
              b.bill_number,
              b.created_at,
              c.name AS customer_name,
              c.phone AS customer_phone,
              b.total_amount,
              b.advance_paid,
              b.due_amount,
              b.status,
              b.payment_mode
            FROM Bills b
            JOIN Customers c ON c.id = b.customer_id
            WHERE b.due_amount > 0
        """
        params = []

        if customer_id:
            base_sql += " AND b.customer_id = ?"
            params.append(int(customer_id))

        if s:
            base_sql += " AND (b.bill_number LIKE ? OR c.name LIKE ? OR c.phone LIKE ?)"
            like = f"%{s}%"
            params.extend([like, like, like])

        base_sql += " ORDER BY b.id DESC LIMIT ?"
        params.append(int(limit))

        rows = con.execute(base_sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def list_customers_for_filter():
    con = get_connection()
    try:
        rows = con.execute(
            "SELECT id, name, phone FROM Customers ORDER BY name COLLATE NOCASE;"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def receive_payment(bill_id: int, amount: float, payment_mode: str):
    if payment_mode not in ("Cash", "UPI", "Bank Transfer"):
        raise ValueError("Invalid payment mode.")

    try:
        amt = float(amount)
    except:
        raise ValueError("Amount must be a number.")

    if amt <= 0:
        raise ValueError("Amount must be greater than 0.")

    con = get_connection()
    try:
        con.execute("BEGIN IMMEDIATE;")

        bill = con.execute(
            "SELECT total_amount, advance_paid FROM Bills WHERE id=?;",
            (int(bill_id),)
        ).fetchone()
        if not bill:
            raise ValueError("Bill not found.")

        total = float(bill["total_amount"] or 0)
        adv = float(bill["advance_paid"] or 0)

        new_adv = adv + amt
        if new_adv > total:
            raise ValueError("Payment is more than due amount.")

        due = total - new_adv
        if new_adv <= 0:
            status = "Due"
        elif new_adv >= total:
            status = "Paid"
        else:
            status = "Partial"

        # store payment record
        con.execute(
            "INSERT INTO Payments(bill_id, amount, payment_mode, paid_at) VALUES (?, ?, ?, ?);",
            (int(bill_id), amt, payment_mode, _now())
        )

        # update bill
        con.execute(
            """
            UPDATE Bills
            SET advance_paid=?,
                due_amount=?,
                status=?,
                payment_mode=?,
                updated_at=?
            WHERE id=?;
            """,
            (new_adv, due, status, payment_mode, _now(), int(bill_id))
        )

        con.commit()
    except:
        con.rollback()
        raise
    finally:
        con.close()
