import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = str(BASE_DIR / "tracker.db")


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS time_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project TEXT NOT NULL,
        description TEXT,
        start_time TEXT NOT NULL,
        end_time TEXT,
        duration_seconds INTEGER
    )
    """)

    conn.commit()
    conn.close()


def reorder_entry_ids(conn: sqlite3.Connection | None = None):
    should_close = conn is None
    if should_close:
        conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT id
        FROM time_entries
        ORDER BY date(start_time) ASC, time(start_time) ASC, id ASC
    """)
    ordered_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("BEGIN")
    try:
        if not ordered_ids:
            cursor.execute(
                "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES(?, ?)",
                ("time_entries", 0)
            )
            conn.commit()
            return

        max_id = len(ordered_ids)
        cursor.execute(
            "INSERT OR REPLACE INTO sqlite_sequence(name, seq) VALUES(?, ?)",
            ("time_entries", max_id)
        )

        id_updates = [
            (old_id, new_id)
            for new_id, old_id in enumerate(ordered_ids, start=1)
            if old_id != new_id
        ]

        if id_updates:
            for old_id, _ in id_updates:
                cursor.execute(
                    "UPDATE time_entries SET id = ? WHERE id = ?",
                    (-old_id, old_id)
                )
            for old_id, new_id in id_updates:
                cursor.execute(
                    "UPDATE time_entries SET id = ? WHERE id = ?",
                    (new_id, -old_id)
                )

        conn.commit()
    except sqlite3.DatabaseError:
        conn.rollback()
        raise
    finally:
        if should_close:
            conn.close()


def _ensure_no_overlap(conn, start_time, end_time, exclude_id=None):
    if start_time is None or end_time is None:
        return

    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except ValueError:
        raise ValueError("Formato de data/hora inválido.")

    if end_dt <= start_dt:
        raise ValueError("O horário de término deve ser depois do início.")

    query = """
        SELECT id, start_time, end_time
        FROM time_entries
        WHERE start_time < ? AND end_time > ?
    """
    params = [end_time, start_time]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)

    cursor = conn.cursor()
    cursor.execute(query, params)
    if cursor.fetchone():
        raise ValueError("Já existe um registro com intervalo de tempo sobreposto.")


def insert_entry(project, description, start_time, end_time, duration_seconds):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    _ensure_no_overlap(conn, start_time, end_time)

    cursor.execute("""
        INSERT INTO time_entries (
            project,
            description,
            start_time,
            end_time,
            duration_seconds
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        project,
        description,
        start_time,
        end_time,
        duration_seconds
    ))

    conn.commit()
    reorder_entry_ids(conn)
    conn.close()


def fetch_entries(project=None, start_date=None, end_date=None, match_mode="exact"):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = """
        SELECT id, project, description, start_time, end_time, duration_seconds
        FROM time_entries
        WHERE 1 = 1
    """
    params = []

    if project:
        if match_mode == "partial":
            query += " AND lower(project) LIKE lower(?)"
            params.append(f"%{project}%")
        else:
            query += " AND lower(project) = lower(?)"
            params.append(project)

    if start_date:
        query += " AND date(start_time) >= date(?)"
        params.append(start_date)

    if end_date:
        query += " AND date(start_time) <= date(?)"
        params.append(end_date)

    query += " ORDER BY date(start_time) DESC, time(start_time) DESC, id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return rows


def fetch_projects():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT project
        FROM time_entries
        WHERE project IS NOT NULL
        ORDER BY project ASC
    """)

    rows = [row[0] for row in cursor.fetchall()]
    conn.close()

    return rows


def update_entry(entry_id, project, description, start_time, end_time, duration_seconds):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    _ensure_no_overlap(conn, start_time, end_time, exclude_id=entry_id)

    cursor.execute("""
        UPDATE time_entries
        SET project = ?,
            description = ?,
            start_time = ?,
            end_time = ?,
            duration_seconds = ?
        WHERE id = ?
    """, (
        project,
        description,
        start_time,
        end_time,
        duration_seconds,
        entry_id
    ))

    conn.commit()
    reorder_entry_ids(conn)
    conn.close()


def delete_entry(entry_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))
    conn.commit()
    reorder_entry_ids(conn)
    conn.close()
