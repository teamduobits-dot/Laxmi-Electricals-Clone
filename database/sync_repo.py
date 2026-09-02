from database.db import get_connection

def enqueue_upload(bill_id: int, file_path: str):
    con = get_connection()
    try:
        # avoid duplicates for same bill/file if already pending
        row = con.execute(
            "SELECT id FROM Sync_Queue WHERE bill_id=? AND file_path=? AND sync_status='PENDING' LIMIT 1;",
            (bill_id, file_path)
        ).fetchone()
        if row:
            return row["id"]

        cur = con.execute(
            "INSERT INTO Sync_Queue(bill_id, file_path, sync_status) VALUES (?, ?, 'PENDING');",
            (bill_id, file_path)
        )
        con.commit()
        return cur.lastrowid
    finally:
        con.close()

def get_pending_uploads(limit: int = 50):
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT id, bill_id, file_path, sync_status
            FROM Sync_Queue
            WHERE sync_status='PENDING'
            ORDER BY id ASC
            LIMIT ?;
            """,
            (int(limit),)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def mark_synced(queue_id: int):
    con = get_connection()
    try:
        con.execute("UPDATE Sync_Queue SET sync_status='SYNCED' WHERE id=?;", (queue_id,))
        con.commit()
    finally:
        con.close()

def mark_failed(queue_id: int):
    """Terminal state for entries whose local PDF no longer exists (avoids infinite PENDING)."""
    con = get_connection()
    try:
        con.execute("UPDATE Sync_Queue SET sync_status='FAILED' WHERE id=?;", (queue_id,))
        con.commit()
    finally:
        con.close()

def pending_count() -> int:
    con = get_connection()
    try:
        row = con.execute("SELECT COUNT(*) AS c FROM Sync_Queue WHERE sync_status='PENDING';").fetchone()
        return int(row["c"] or 0)
    finally:
        con.close()
