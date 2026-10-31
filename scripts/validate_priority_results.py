import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.engine.priority_engine import classify_priority

rules = load_business_rules()
errors = []

with get_connection() as connection:

    rule_ids = {
        row[1]: row[0]
        for row in connection.execute("""
            SELECT priority_rule_id, priority
            FROM priority_rule
            WHERE is_active = 1
        """).fetchall()
    }

    rows = connection.execute("""
        SELECT
            c.complaint_id,
            c.category_id,
            c.severity,
            c.sentiment,
            c.is_repeat,
            cu.is_vulnerable,
            p.is_safety_critical,
            o.order_total_paise,
            c.priority,
            c.priority_rule_id
        FROM complaint c
        JOIN customer cu ON cu.customer_id = c.customer_id
        LEFT JOIN product p ON p.product_id = c.product_id
        LEFT JOIN customer_order o ON o.order_id = c.order_id
    """).fetchall()

    for row in rows:
        complaint = {
            "category_id": row[1],
            "severity": row[2],
            "sentiment": row[3],
            "is_repeat": row[4],
            "is_vulnerable": row[5],
            "is_safety_critical": row[6] or 0,
            "order_total_paise": row[7],
        }

        expected_priority = classify_priority(complaint, rules)
        expected_rule_id = rule_ids[expected_priority]

        if row[8] != expected_priority:
            errors.append(
                f"{row[0]}: priority mismatch "
                f"(stored={row[8]}, expected={expected_priority})"
            )

        if row[9] != expected_rule_id:
            errors.append(
                f"{row[0]}: rule ID mismatch "
                f"(stored={row[9]}, expected={expected_rule_id})"
            )

    print("PRIORITY VALIDATION")
    print("===================")
    print("Complaints checked:", len(rows))
    print("Validation errors:", len(errors))

    if errors:
        for error in errors[:20]:
            print(error)
    else:
        print("All priority decisions and rule references are consistent.")

    print("\nPRIORITY DISTRIBUTION")
    for row in connection.execute("""
        SELECT priority, COUNT(*)
        FROM complaint
        GROUP BY priority
        ORDER BY priority
    """):
        print(row)

if errors:
    raise SystemExit(1)