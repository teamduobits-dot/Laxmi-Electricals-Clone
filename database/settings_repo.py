from database.db import get_connection

def get_setting(key: str, default=None):
    con = get_connection()
    try:
        row = con.execute("SELECT value FROM Settings WHERE key=?;", (key,)).fetchone()
        return row["value"] if row else default
    finally:
        con.close()

def set_setting(key: str, value: str):
    con = get_connection()
    try:
        con.execute(
            "INSERT OR REPLACE INTO Settings(key, value) VALUES(?, ?);",
            (str(key), str(value)),
        )
        con.commit()
    finally:
        con.close()

def get_business_profile(default_name: str, default_phone: str, default_address: str) -> dict:
    return {
        "name": get_setting("business_name", default_name),
        "phone": get_setting("business_phone", default_phone),
        "address": get_setting("business_address", default_address),
    }

def save_business_profile(name: str, phone: str, address: str):
    set_setting("business_name", (name or "").strip())
    set_setting("business_phone", (phone or "").strip())
    set_setting("business_address", (address or "").strip())
