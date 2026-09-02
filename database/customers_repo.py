import sqlite3
from datetime import datetime
from database.db import get_connection
from utils.formatting import smart_title
from utils.validators import clean_phone, is_valid_phone

def _now():
    return datetime.now().isoformat(timespec="seconds")

def _check_phone_unique(phone: str, exclude_id: int | None = None):
    con = get_connection()
    try:
        if exclude_id:
            row = con.execute("SELECT id FROM Customers WHERE phone=? AND id != ? LIMIT 1;", (phone, int(exclude_id))).fetchone()
        else:
            row = con.execute("SELECT id FROM Customers WHERE phone=? LIMIT 1;", (phone,)).fetchone()
        if row:
            raise ValueError(f"Phone number {phone} already exists for another customer.")
    finally:
        con.close()

def create_customer(name: str, phone: str = "", address: str = "") -> int:
    name = smart_title((name or "").strip())
    phone = clean_phone(phone)
    address = (address or "").strip()

    if not name:
        raise ValueError("Customer name is required.")
    if len(name) < 2:
        raise ValueError("Customer name must be at least 2 characters.")
    if not is_valid_phone(phone):
        raise ValueError("Phone number must be 10 digits (numbers only).")
    
    _check_phone_unique(phone)

    con = get_connection()
    try:
        cur = con.execute(
            "INSERT INTO Customers(name, phone, address, created_at) VALUES (?, ?, ?, ?);",
            (name, phone, address, _now()),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def update_customer(customer_id: int, name: str, phone: str = "", address: str = "") -> None:
    name = smart_title((name or "").strip())
    phone = clean_phone(phone)
    address = (address or "").strip()

    if not name:
        raise ValueError("Customer name is required.")
    if len(name) < 2:
        raise ValueError("Customer name must be at least 2 characters.")
    if not is_valid_phone(phone):
        raise ValueError("Phone number must be 10 digits (numbers only).")

    _check_phone_unique(phone, exclude_id=customer_id)

    con = get_connection()
    try:
        con.execute(
            "UPDATE Customers SET name=?, phone=?, address=? WHERE id=?;",
            (name, phone, address, customer_id),
        )
        con.commit()
    finally:
        con.close()

def delete_customer(customer_id: int) -> None:
    con = get_connection()
    try:
        con.execute("DELETE FROM Customers WHERE id=?;", (customer_id,))
        con.commit()
    except sqlite3.IntegrityError as e:
        raise ValueError("Cannot delete: bills exist for this customer. Delete bills first.") from e
    finally:
        con.close()

def get_customer(customer_id: int):
    con = get_connection()
    try:
        return con.execute("SELECT * FROM Customers WHERE id=?;", (customer_id,)).fetchone()
    finally:
        con.close()

def _where(query: str):
    q = (query or "").strip()
    if not q:
        return ("", [])
    like = f"%{q}%"
    return ("WHERE c.name LIKE ? OR c.phone LIKE ? OR c.address LIKE ?", [like, like, like])

def count_customers(query: str = "") -> int:
    where_sql, params = _where(query)
    con = get_connection()
    try:
        row = con.execute(
            f"SELECT COUNT(*) AS c FROM Customers c {where_sql};",
            tuple(params)
        ).fetchone()
        return int(row["c"] or 0)
    finally:
        con.close()

def search_customers(query: str = "", limit: int = 50, offset: int = 0):
    """
    Returns: customer rows + bill_count, paginated + stats.
    """
    where_sql, params = _where(query)

    con = get_connection()
    try:
        rows = con.execute(
            f"""
            SELECT
              c.*,
              (SELECT COUNT(*) FROM Bills b WHERE b.customer_id = c.id) AS bill_count,
              COALESCE((SELECT SUM(b.total_amount) FROM Bills b WHERE b.customer_id = c.id),0) AS total_billed,
              COALESCE((SELECT SUM(b.due_amount) FROM Bills b WHERE b.customer_id = c.id),0) AS total_due
            FROM Customers c
            {where_sql}
            ORDER BY c.id DESC
            LIMIT ? OFFSET ?;
            """,
            tuple(params) + (int(limit), int(offset))
        ).fetchall()
        return rows
    finally:
        con.close()
