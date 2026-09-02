from datetime import datetime
from database.db import get_connection
from utils.formatting import smart_title

def _now():
    return datetime.now().isoformat(timespec="seconds")

def _check_unique(service_name: str, exclude_id: int | None = None):
    con = get_connection()
    try:
        if exclude_id:
            row = con.execute(
                "SELECT id FROM Services WHERE LOWER(service_name)=LOWER(?) AND id != ? LIMIT 1;",
                (service_name, int(exclude_id))
            ).fetchone()
        else:
            row = con.execute(
                "SELECT id FROM Services WHERE LOWER(service_name)=LOWER(?) LIMIT 1;",
                (service_name,)
            ).fetchone()
        if row:
            raise ValueError(f"Service '{service_name}' already exists.")
    finally:
        con.close()

def create_service(service_name: str, default_price: float = 0.0) -> int:
    service_name = smart_title((service_name or "").strip())
    if not service_name:
        raise ValueError("Service name is required.")
    if len(service_name) < 2:
        raise ValueError("Service name must be at least 2 characters.")

    try:
        price = float(default_price)
    except:
        raise ValueError("Default price must be a number.")
    if price < 0:
        raise ValueError("Price cannot be negative.")
    if price > 1000000:
        raise ValueError("Price seems too high (max 10,00,000).")

    _check_unique(service_name)

    con = get_connection()
    try:
        cur = con.execute(
            "INSERT INTO Services(service_name, default_price, created_at) VALUES (?, ?, ?);",
            (service_name, price, _now()),
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def update_service(service_id: int, service_name: str, default_price: float = 0.0) -> None:
    service_name = smart_title((service_name or "").strip())
    if not service_name:
        raise ValueError("Service name is required.")
    if len(service_name) < 2:
        raise ValueError("Service name must be at least 2 characters.")

    try:
        price = float(default_price)
    except:
        raise ValueError("Default price must be a number.")
    if price < 0:
        raise ValueError("Price cannot be negative.")

    _check_unique(service_name, exclude_id=service_id)

    con = get_connection()
    try:
        con.execute(
            "UPDATE Services SET service_name=?, default_price=? WHERE id=?;",
            (service_name, price, service_id),
        )
        con.commit()
    finally:
        con.close()

def delete_service(service_id: int) -> None:
    con = get_connection()
    try:
        con.execute("DELETE FROM Services WHERE id=?;", (service_id,))
        con.commit()
    finally:
        con.close()

def get_service(service_id: int):
    con = get_connection()
    try:
        return con.execute("SELECT * FROM Services WHERE id=?;", (service_id,)).fetchone()
    finally:
        con.close()

def search_services(query: str = ""):
    q = (query or "").strip()
    con = get_connection()
    try:
        if not q:
            return con.execute("SELECT * FROM Services ORDER BY service_name COLLATE NOCASE;").fetchall()

        like = f"%{q}%"
        return con.execute(
            "SELECT * FROM Services WHERE service_name LIKE ? ORDER BY service_name COLLATE NOCASE;",
            (like,),
        ).fetchall()
    finally:
        con.close()

def service_usage_count(service_id: int) -> int:
    # Count how many bill items used this service name
    con = get_connection()
    try:
        srv = con.execute("SELECT service_name FROM Services WHERE id=?", (service_id,)).fetchone()
        if not srv:
            return 0
        name = srv["service_name"]
        row = con.execute("SELECT COUNT(*) AS c FROM Bill_Items WHERE service_name=? COLLATE NOCASE;", (name,)).fetchone()
        return int(row["c"] or 0)
    finally:
        con.close()
