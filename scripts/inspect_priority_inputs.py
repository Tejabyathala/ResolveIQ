import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection

with get_connection() as connection:

    queries = {
        "Complaints without orders": """
            SELECT COUNT(*) FROM complaint WHERE order_id IS NULL
        """,
        "Complaints without products": """
            SELECT COUNT(*) FROM complaint WHERE product_id IS NULL
        """,
        "Vulnerable customers": """
            SELECT COUNT(*) FROM customer WHERE is_vulnerable = 1
        """,
        "Safety-critical products": """
            SELECT COUNT(*) FROM product WHERE is_safety_critical = 1
        """,
        "Complaints by severity": """
            SELECT severity, COUNT(*)
            FROM complaint
            GROUP BY severity
        """,
        "Complaints by sentiment": """
            SELECT sentiment, COUNT(*)
            FROM complaint
            GROUP BY sentiment
        """,
        "Repeat complaints": """
            SELECT COUNT(*) FROM complaint WHERE is_repeat = 1
        """,
    }

    print("PRIORITY ENGINE INPUT SUMMARY")
    print("=============================")

    for title, query in queries.items():
        print(f"\n{title}:")
        for row in connection.execute(query).fetchall():
            print(row)

    print("\nEXISTING PRIORITY RULES:")
    for row in connection.execute("""
        SELECT priority_rule_id, rule_name, priority, conditions_json
        FROM priority_rule
        ORDER BY priority_rule_id
    """).fetchall():
        print(row)