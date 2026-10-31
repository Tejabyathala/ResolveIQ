
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


def check_complaint_dates():
    with get_connection() as connection:

        checks = {
            "Complaints before customer creation": """
                SELECT COUNT(*)
                FROM complaint x
                JOIN customer u
                    ON x.customer_id = u.customer_id
                WHERE x.created_at < u.created_at
            """,

            "Complaints after reference date": """
                SELECT COUNT(*)
                FROM complaint
                WHERE created_at > '2026-10-22T00:00:00+00:00'
            """,

            "Orders dated after complaints": """
                SELECT COUNT(*)
                FROM complaint x
                JOIN customer_order o
                    ON x.order_id = o.order_id
                WHERE date(x.created_at) < o.order_date
            """,

            "Repeat complaints outside 30 days": """
                SELECT COUNT(*)
                FROM complaint x
                JOIN complaint p
                    ON x.repeat_of_complaint_id = p.complaint_id
                WHERE julianday(x.created_at) -
                      julianday(p.created_at) > 30
                   OR julianday(x.created_at) -
                      julianday(p.created_at) <= 0
            """
        }

        print("\nCOMPLAINT DATE VALIDATION")
        print("=========================")

        for label, query in checks.items():
            result = connection.execute(query).fetchone()[0]
            print(f"{label}: {result}")


if __name__ == "__main__":
    check_complaint_dates()
