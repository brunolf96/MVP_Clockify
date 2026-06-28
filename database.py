import sqlite3
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


def insert_entry(project, description, start_time, end_time, duration_seconds):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

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

    query += " ORDER BY start_time DESC, id DESC"

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
    conn.close()


def delete_entry(entry_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
