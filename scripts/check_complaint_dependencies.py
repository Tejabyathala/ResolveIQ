
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


tables = [
    "assignment",
    "complaint_message",
    "sla_clock",
    "complaint_status_event",
    "resolution",
]

with get_connection() as connection:
    print("COMPLAINT DEPENDENCY CHECK")
    print("==========================")

    for table in tables:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count}")
