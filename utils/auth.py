import bcrypt
from database.db import get_connection

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(password: str, stored_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))

def has_admin_password() -> bool:
    con = get_connection()
    try:
        row = con.execute("SELECT id FROM Users LIMIT 1;").fetchone()
        return row is not None
    finally:
        con.close()

def set_admin_password(password: str):
    pw_hash = hash_password(password)
    con = get_connection()
    try:
        con.execute("DELETE FROM Users;")  # single-user only
        con.execute("INSERT INTO Users(password_hash) VALUES (?);", (pw_hash,))
        con.commit()
    finally:
        con.close()

def check_login(password: str) -> bool:
    con = get_connection()
    try:
        row = con.execute("SELECT password_hash FROM Users LIMIT 1;").fetchone()
        if not row:
            return False
        return verify_password(password, row["password_hash"])
    finally:
        con.close()

def change_admin_password(current_password: str, new_password: str):
    current_password = (current_password or "").strip()
    new_password = (new_password or "").strip()

    if len(new_password) < 4:
        raise ValueError("New password must be at least 4 characters.")

    con = get_connection()
    try:
        row = con.execute("SELECT id, password_hash FROM Users LIMIT 1;").fetchone()
        if not row:
            raise ValueError("Admin password not set.")

        if not verify_password(current_password, row["password_hash"]):
            raise ValueError("Current password is incorrect.")

        new_hash = hash_password(new_password)
        con.execute("UPDATE Users SET password_hash=? WHERE id=?;", (new_hash, row["id"]))
        con.commit()
    finally:
        con.close()
