
from datetime import datetime

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.generator.complaint_generator import generate_complaints


def save_complaints():
    rules = load_business_rules()

    complaint_count = rules["generation"]["scale"]["complaints"]
    seed = rules["generation"]["seed"]

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    with get_connection() as connection:

        # Load customers.
        customers = [
            {
            "customer_id": row[0],
            "created_at": row[1],
            }
            for row in connection.execute("""
                SELECT customer_id, created_at
                FROM customer
                ORDER BY customer_id
                """).fetchall()
        ]

        # Load orders.
        orders = [
            {
                "order_id": row[0],
                "customer_id": row[1],
                "order_date": row[2],
            }
            for row in connection.execute("""
                SELECT order_id, customer_id, order_date
                FROM customer_order
                ORDER BY order_id
            """).fetchall()
        ]

        # Load order items.
        order_items = [
            {
                "order_id": row[0],
                "product_id": row[1],
            }
            for row in connection.execute("""
                SELECT order_id, product_id
                FROM order_item
                ORDER BY order_item_id
            """).fetchall()
        ]

        # Load complaint categories.
        categories = [
            {"category_id": row[0]}
            for row in connection.execute("""
                SELECT category_id
                FROM category
                WHERE is_active = 1
                ORDER BY category_id
            """).fetchall()
        ]

        if not customers or not orders or not categories:
            raise ValueError(
                "Required master data is missing. "
                "Generate customers, orders and categories first."
            )

        # Generate complaints.
        complaints = generate_complaints(
            customers,
            orders,
            order_items,
            categories,
            complaint_count,
            seed,
            reference_datetime,
        )

        # Prepare database records.
        complaint_records = [
            (
                item["complaint_id"],
                item["customer_id"],
                item["order_id"],
                item["product_id"],
                item["category_id"],
                item["priority_rule_id"],
                item["subject"],
                item["description"],
                item["channel"],
                item["sentiment"],
                item["severity"],
                item["priority"],
                item["is_repeat"],
                item["repeat_of_complaint_id"],
                item["current_status"],
                item["created_at"],
                item["closed_at"],
            )
            for item in complaints
        ]

        # Insert complaints.
        connection.executemany("""
            INSERT OR IGNORE INTO complaint
            (
                complaint_id,
                customer_id,
                order_id,
                product_id,
                category_id,
                priority_rule_id,
                subject,
                description,
                channel,
                sentiment,
                severity,
                priority,
                is_repeat,
                repeat_of_complaint_id,
                current_status,
                created_at,
                closed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, complaint_records)

        # Check customer and order consistency.
        customer_order_errors = connection.execute("""
            SELECT COUNT(*)
            FROM complaint c
            JOIN customer_order o ON c.order_id = o.order_id
            WHERE c.customer_id != o.customer_id
        """).fetchone()[0]

        # Check whether complaint products belong to their orders.
        product_order_errors = connection.execute("""
            SELECT COUNT(*)
            FROM complaint c
            WHERE c.product_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM order_item oi
                  WHERE oi.order_id = c.order_id
                    AND oi.product_id = c.product_id
              )
        """).fetchone()[0]

        # Check repeat complaint relationships.
        repeat_errors = connection.execute("""
            SELECT COUNT(*)
            FROM complaint c
            LEFT JOIN complaint previous
                ON c.repeat_of_complaint_id = previous.complaint_id
            WHERE c.is_repeat = 1
              AND (
                  previous.complaint_id IS NULL
                  OR c.customer_id != previous.customer_id
                  OR c.category_id != previous.category_id
                  OR c.created_at <= previous.created_at
              )
        """).fetchone()[0]

        saved_complaints = connection.execute(
            "SELECT COUNT(*) FROM complaint"
        ).fetchone()[0]

        repeat_count = connection.execute("""
            SELECT COUNT(*)
            FROM complaint
            WHERE is_repeat = 1
        """).fetchone()[0]

        if customer_order_errors or product_order_errors or repeat_errors:
            raise ValueError(
                "Complaint relationship validation failed."
            )

    print("\nCOMPLAINT GENERATION SUMMARY")
    print("============================")
    print(f"Generated complaints: {len(complaints)}")
    print(f"Complaints in database: {saved_complaints}")
    print(f"Repeat complaints: {repeat_count}")
    print(f"Customer-order errors: {customer_order_errors}")
    print(f"Product-order errors: {product_order_errors}")
    print(f"Repeat relationship errors: {repeat_errors}")


if __name__ == "__main__":
    save_complaints()
