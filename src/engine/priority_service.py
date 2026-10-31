from collections import Counter

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.engine.priority_engine import classify_priority


def classify_all_complaints():
    rules = load_business_rules()

    with get_connection() as connection:

        # Get the database IDs corresponding to P1, P2, P3 and P4.
        priority_rule_ids = {
            row[1]: row[0]
            for row in connection.execute("""
                SELECT priority_rule_id, priority
                FROM priority_rule
                WHERE is_active = 1
            """).fetchall()
        }

        required_priorities = {"P1", "P2", "P3", "P4"}

        if not required_priorities.issubset(priority_rule_ids):
            raise ValueError("Missing active priority rules in database.")

        # Retrieve complaint data and related customer, product and order data.
        rows = connection.execute("""
            SELECT
                c.complaint_id,
                c.category_id,
                c.severity,
                c.sentiment,
                c.is_repeat,
                cu.is_vulnerable,
                p.is_safety_critical,
                o.order_total_paise
            FROM complaint c
            JOIN customer cu
                ON cu.customer_id = c.customer_id
            LEFT JOIN product p
                ON p.product_id = c.product_id
            LEFT JOIN customer_order o
                ON o.order_id = c.order_id
            ORDER BY c.complaint_id
        """).fetchall()

        updates = []
        priority_counts = Counter()

        for row in rows:
            complaint = {
                "complaint_id": row[0],
                "category_id": row[1],
                "severity": row[2],
                "sentiment": row[3],
                "is_repeat": row[4],
                "is_vulnerable": row[5],
                "is_safety_critical": row[6] or 0,
                "order_total_paise": row[7],
            }

            priority = classify_priority(complaint, rules)
            priority_rule_id = priority_rule_ids[priority]

            updates.append((
                priority,
                priority_rule_id,
                complaint["complaint_id"],
            ))

            priority_counts[priority] += 1

        # Update all complaints in one transaction.
        connection.executemany("""
            UPDATE complaint
            SET priority = ?,
                priority_rule_id = ?
            WHERE complaint_id = ?
        """, updates)

        classified_count = connection.execute("""
            SELECT COUNT(*)
            FROM complaint
            WHERE priority IS NOT NULL
        """).fetchone()[0]

        if classified_count != len(rows):
            raise ValueError("Not all complaints were classified.")

    print("\nPRIORITY CLASSIFICATION SUMMARY")
    print("===============================")
    print("Complaints processed:", len(rows))

    for priority in ["P1", "P2", "P3", "P4"]:
        print(f"{priority}: {priority_counts[priority]}")

    print("Total classified:", sum(priority_counts.values()))


if __name__ == "__main__":
    classify_all_complaints()