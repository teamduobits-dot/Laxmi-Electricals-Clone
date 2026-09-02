from database.db import get_connection

def daily_summary(date_yyyy_mm_dd: str) -> dict:
    con = get_connection()
    try:
        row = con.execute(
            """
            SELECT
              COUNT(*) AS bill_count,
              COALESCE(SUM(total_amount), 0) AS total,
              COALESCE(SUM(advance_paid), 0) AS received,
              COALESCE(SUM(due_amount), 0) AS due
            FROM Bills
            WHERE date(created_at) = date(?);
            """,
            (date_yyyy_mm_dd,)
        ).fetchone()

        return dict(row) if row else {"bill_count": 0, "total": 0, "received": 0, "due": 0}
    finally:
        con.close()

def daily_bills(date_yyyy_mm_dd: str):
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT
              b.id, b.bill_number, b.created_at, c.name AS customer_name,
              b.subtotal, b.discount_amount, b.tax_amount, b.total_amount,
              b.advance_paid, b.due_amount, b.status, b.payment_mode
            FROM Bills b
            JOIN Customers c ON c.id = b.customer_id
            WHERE date(b.created_at) = date(?)
            ORDER BY b.id DESC;
            """,
            (date_yyyy_mm_dd,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def monthly_summary(year: int, month: int) -> dict:
    ym = f"{int(year):04d}-{int(month):02d}"
    con = get_connection()
    try:
        row = con.execute(
            """
            SELECT
              COUNT(*) AS bill_count,
              COALESCE(SUM(total_amount), 0) AS total,
              COALESCE(SUM(advance_paid), 0) AS received,
              COALESCE(SUM(due_amount), 0) AS due
            FROM Bills
            WHERE strftime('%Y-%m', created_at) = ?;
            """,
            (ym,)
        ).fetchone()

        return dict(row) if row else {"bill_count": 0, "total": 0, "received": 0, "due": 0}
    finally:
        con.close()

def monthly_bills(year: int, month: int):
    ym = f"{int(year):04d}-{int(month):02d}"
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT
              b.id, b.bill_number, b.created_at, c.name AS customer_name,
              b.subtotal, b.discount_amount, b.tax_amount, b.total_amount,
              b.advance_paid, b.due_amount, b.status, b.payment_mode
            FROM Bills b
            JOIN Customers c ON c.id = b.customer_id
            WHERE strftime('%Y-%m', b.created_at) = ?
            ORDER BY b.id DESC;
            """,
            (ym,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def available_years():
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT DISTINCT strftime('%Y', created_at) AS y
            FROM Bills
            WHERE y IS NOT NULL
            ORDER BY y DESC;
            """
        ).fetchall()
        years = [int(r["y"]) for r in rows if r["y"]]
        return years
    finally:
        con.close()
