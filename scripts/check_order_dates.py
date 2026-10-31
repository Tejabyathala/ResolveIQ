import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection

with get_connection() as connection:
    errors = connection.execute("""
        SELECT COUNT(*)
        FROM customer_order o
        JOIN customer c ON c.customer_id = o.customer_id
        WHERE o.order_date < date(c.created_at)
    """).fetchone()[0]

    print("ORDER DATE VALIDATION")
    print("=====================")
    print("Orders before customer creation:", errors)