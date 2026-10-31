import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection

dependent_tables = [
    "assignment",
    "complaint_message",
    "sla_clock",
    "sla_event",
    "complaint_status_event",
    "resolution",
    "survey",
]

with get_connection() as connection:
    for table in dependent_tables:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        if count > 0:
            raise RuntimeError(
                f"Cannot reset: {table} contains {count} records."
            )

    connection.execute("PRAGMA defer_foreign_keys = ON")

    connection.execute("DELETE FROM complaint")
    connection.execute("DELETE FROM order_item")
    connection.execute("DELETE FROM customer_order")

    print("Old complaints, order items and orders removed.")