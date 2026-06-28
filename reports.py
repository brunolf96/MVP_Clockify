import csv
import sqlite3
from collections import defaultdict

from database import DB_NAME
from utils import format_seconds


def get_all_entries():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT project, description, start_time, end_time, duration_seconds
        FROM time_entries
        ORDER BY start_time DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def get_all_entries_with_id():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, project, description, start_time, end_time, duration_seconds
        FROM time_entries
        ORDER BY start_time DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return rows


def build_report_text():
    entries = get_all_entries_with_id()

    if not entries:
        return "Nenhuma entrada encontrada."

    lines = ["===== HISTÓRICO =====", ""]

    for entry_id, project, desc, start, end, duration in entries:
        lines.append(f"[{entry_id}] {project}")
        lines.append(f"Descrição: {desc or ''}")
        lines.append(f"Início: {start or ''}")
        lines.append(f"Fim: {end or ''}")
        lines.append(f"Duração: {format_seconds(duration or 0)}")
        lines.append("-" * 30)

    return "\n".join(lines)


def build_summary_text():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT project, SUM(duration_seconds)
        FROM time_entries
        GROUP BY project
        ORDER BY SUM(duration_seconds) DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return "Nenhuma entrada encontrada."

    total_seconds = sum(row[1] or 0 for row in rows)
    lines = ["===== RESUMO POR PROJETO =====", ""]

    for project, seconds in rows:
        lines.append(f"{project} — {format_seconds(seconds or 0)}")

    lines.append("")
    lines.append(f"TOTAL GERAL: {format_seconds(total_seconds)}")

    return "\n".join(lines)


def export_entries_to_csv(path, entries=None):
    if entries is None:
        entries = get_all_entries_with_id()

    with open(path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["ID", "Projeto", "Descrição", "Início", "Fim", "Duração"])

        for entry_id, project, desc, start, end, duration in entries:
            writer.writerow([
                entry_id,
                project,
                desc or "",
                start or "",
                end or "",
                format_seconds(duration or 0)
            ])


def print_report():
    report = build_report_text()
    print(report)


def project_summary():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT project, duration_seconds
        FROM time_entries
    """)

    rows = cursor.fetchall()
    conn.close()

    summary = defaultdict(int)

    for project, duration in rows:
        summary[project] += duration or 0

    print("\n===== RESUMO POR PROJETO =====\n")

    total = 0

    for project, seconds in summary.items():
        total += seconds
        print(f"{project} — {format_seconds(seconds)}")

    print("\n----------------------------")
    print(f"TOTAL GERAL: {total/3600:.2f} horas\n")
