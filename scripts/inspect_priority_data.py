import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection

with get_connection() as connection:
    print("COMPLAINT COLUMNS")
    print("=================")

    for row in connection.execute("PRAGMA table_info(complaint)"):
        print(row[1], "-", row[2])

    print("\nSAMPLE COMPLAINTS")
    print("=================")

    rows = connection.execute("""
        SELECT
            complaint_id,
            customer_id,
            product_id,
            severity,
            sentiment,
            is_repeat,
            priority
        FROM complaint
        LIMIT 5
    """).fetchall()

    for row in rows:
        print(row)