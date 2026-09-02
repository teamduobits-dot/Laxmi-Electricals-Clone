from database.db import get_connection

def list_customers():
    con = get_connection()
    try:
        return con.execute(
            "SELECT id, name, phone FROM Customers ORDER BY name COLLATE NOCASE;"
        ).fetchall()
    finally:
        con.close()

def list_services():
    con = get_connection()
    try:
        return con.execute(
            "SELECT id, service_name, default_price FROM Services ORDER BY service_name COLLATE NOCASE;"
        ).fetchall()
    finally:
        con.close()
