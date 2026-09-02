import sys
from pathlib import Path

# Ensure project root is in sys.path (so "database" import works)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database.db import get_connection, init_db
from utils.formatting import smart_title

def normalize_table(table: str, id_col: str, text_col: str):
    con = get_connection()
    try:
        rows = con.execute(f"SELECT {id_col}, {text_col} FROM {table};").fetchall()
        updated = 0
        for r in rows:
            rid = r[id_col]
            old = r[text_col] or ""
            new = smart_title(old)
            if new != old:
                con.execute(f"UPDATE {table} SET {text_col}=? WHERE {id_col}=?;", (new, rid))
                updated += 1
        con.commit()
        return updated
    finally:
        con.close()

def main():
    init_db()
    u1 = normalize_table("Customers", "id", "name")
    u2 = normalize_table("Services", "id", "service_name")
    u3 = normalize_table("Bill_Items", "id", "service_name")
    print("Normalized:")
    print(" Customers :", u1)
    print(" Services  :", u2)
    print(" Bill_Items:", u3)

if __name__ == "__main__":
    main()
