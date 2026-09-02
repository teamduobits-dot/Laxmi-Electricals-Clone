from database.db import get_connection

def list_bills_for_customer(customer_id: int):
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT
              id, bill_number, created_at,
              total_amount, advance_paid, due_amount,
              status, payment_mode
            FROM Bills
            WHERE customer_id=?
            ORDER BY id DESC;
            """,
            (int(customer_id),)
        ).fetchall()

        return [dict(r) for r in rows]
    finally:
        con.close()

def customer_bill_stats(customer_id: int) -> dict:
    con = get_connection()
    try:
        row = con.execute(
            """
            SELECT
              COUNT(*) AS bill_count,
              COALESCE(SUM(total_amount), 0) AS total_amount,
              COALESCE(SUM(advance_paid), 0) AS received,
              COALESCE(SUM(due_amount), 0) AS due
            FROM Bills
            WHERE customer_id=?;
            """,
            (int(customer_id),)
        ).fetchone()
        return dict(row) if row else {"bill_count": 0, "total_amount": 0, "received": 0, "due": 0}
    finally:
        con.close()
