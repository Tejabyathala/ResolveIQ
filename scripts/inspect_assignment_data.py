import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection

with get_connection() as connection:

    print("TEAM AND AGENT SUMMARY")
    print("======================")

    rows = connection.execute("""
        SELECT
            t.team_id,
            t.team_name,
            COUNT(a.agent_id) AS total_agents,
            SUM(CASE WHEN a.is_active = 1 THEN 1 ELSE 0 END)
                AS active_agents
        FROM team t
        LEFT JOIN agent a ON a.team_id = t.team_id
        GROUP BY t.team_id, t.team_name
        ORDER BY t.team_id
    """).fetchall()

    for row in rows:
        print(row)

    print("\nASSIGNMENT TABLE COLUMNS")
    print("=======================")

    for row in connection.execute(
        "PRAGMA table_info(assignment)"
    ):
        print(row[1], "-", row[2])

    print("\nEXISTING ASSIGNMENTS")
    print("====================")

    print(
        "Total assignments:",
        connection.execute(
            "SELECT COUNT(*) FROM assignment"
        ).fetchone()[0]
    )

    print(
        "Current assignments:",
        connection.execute(
            "SELECT COUNT(*) FROM assignment WHERE is_current = 1"
        ).fetchone()[0]
    )

    print("\nCOMPLAINT STATUS DISTRIBUTION")
    print("=============================")

    for row in connection.execute("""
        SELECT current_status, COUNT(*)
        FROM complaint
        GROUP BY current_status
        ORDER BY current_status
    """):
        print(row)