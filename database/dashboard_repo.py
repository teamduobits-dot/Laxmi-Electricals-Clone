from datetime import datetime
from database.db import get_connection

def _today_str():
    return datetime.now().strftime("%Y-%m-%d")

def _month_str():
    return datetime.now().strftime("%Y-%m")

def _prev_month_str():
    y = datetime.now().year
    m = datetime.now().month
    if m == 1:
        return f"{y-1}-12"
    return f"{y}-{m-1:02d}"

def get_dashboard_stats():
    con = get_connection()
    try:
        today = _today_str()
        month = _month_str()
        prev_month = _prev_month_str()

        # Today's collection = advance_paid today
        today_earnings = con.execute(
            "SELECT COALESCE(SUM(advance_paid), 0) AS v FROM Bills WHERE date(created_at) = date(?);",
            (today,)
        ).fetchone()["v"]

        month_earnings = con.execute(
            "SELECT COALESCE(SUM(advance_paid), 0) AS v FROM Bills WHERE strftime('%Y-%m', created_at) = ?;",
            (month,)
        ).fetchone()["v"]

        prev_month_earnings = con.execute(
            "SELECT COALESCE(SUM(advance_paid), 0) AS v FROM Bills WHERE strftime('%Y-%m', created_at) = ?;",
            (prev_month,)
        ).fetchone()["v"]

        pending_dues = con.execute(
            "SELECT COALESCE(SUM(due_amount), 0) AS v FROM Bills WHERE due_amount > 0;"
        ).fetchone()["v"]

        pending_count = con.execute(
            "SELECT COUNT(*) AS c FROM Bills WHERE due_amount > 0;"
        ).fetchone()["c"]

        active_customers = con.execute(
            "SELECT COUNT(DISTINCT customer_id) AS c FROM Bills WHERE strftime('%Y-%m', created_at) = ?;",
            (month,)
        ).fetchone()["c"]

        total_customers = con.execute("SELECT COUNT(*) AS c FROM Customers;").fetchone()["c"]
        total_bills = con.execute("SELECT COUNT(*) AS c FROM Bills;").fetchone()["c"]
        total_revenue = con.execute("SELECT COALESCE(SUM(total_amount),0) AS v FROM Bills;").fetchone()["v"]

        # Growth % vs prev month
        try:
            if float(prev_month_earnings or 0) > 0:
                growth = ((float(month_earnings or 0) - float(prev_month_earnings or 0)) / float(prev_month_earnings or 0)) * 100
            else:
                growth = 100 if float(month_earnings or 0) > 0 else 0
        except:
            growth = 0

        return {
            "today_earnings": float(today_earnings or 0),
            "month_earnings": float(month_earnings or 0),
            "prev_month_earnings": float(prev_month_earnings or 0),
            "pending_dues": float(pending_dues or 0),
            "pending_count": int(pending_count or 0),
            "active_customers": int(active_customers or 0),
            "total_customers": int(total_customers or 0),
            "total_bills": int(total_bills or 0),
            "total_revenue": float(total_revenue or 0),
            "growth_percent": round(growth, 1),
        }
    finally:
        con.close()

def get_recent_bills(limit: int = 8):
    con = get_connection()
    try:
        rows = con.execute(
            """
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
              b.payment_mode,
              b.subtotal,
              b.discount_amount,
              b.tax_amount
            FROM Bills b
            JOIN Customers c ON c.id = b.customer_id
            ORDER BY b.id DESC
            LIMIT ?;
            """,
            (int(limit),)
        ).fetchall()

        return [dict(r) for r in rows]
    finally:
        con.close()

def get_top_customers(limit: int = 5):
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT c.id, c.name, c.phone,
                   COUNT(b.id) AS bill_count,
                   COALESCE(SUM(b.total_amount),0) AS total,
                   COALESCE(SUM(b.due_amount),0) AS due
            FROM Customers c
            LEFT JOIN Bills b ON b.customer_id = c.id
            GROUP BY c.id
            ORDER BY total DESC
            LIMIT ?;
            """,
            (int(limit),)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
