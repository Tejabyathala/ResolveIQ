
from datetime import datetime

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.generator.order_generator import generate_orders


def save_orders():
    rules = load_business_rules()

    order_count = rules["generation"]["scale"]["orders"]
    seed = rules["generation"]["seed"]

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    with get_connection() as connection:

        # Load existing customers.
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
        # Load existing products.
        products = [
            {
                "product_id": row[0],
                "unit_price_paise": row[1],
            }
            for row in connection.execute("""
                SELECT product_id, unit_price_paise
                FROM product
                WHERE is_active = 1
                ORDER BY product_id
            """).fetchall()
        ]

        if not customers:
            raise ValueError("No customers found. Generate customers first.")

        if not products:
            raise ValueError("No active products found. Seed products first.")

        # Generate orders and order items.
        orders, order_items = generate_orders(
            customers,
            products,
            order_count,
            seed,
            reference_datetime,
        )

        # Save orders.
        connection.executemany("""
            INSERT OR IGNORE INTO customer_order
            (
                order_id,
                customer_id,
                order_date,
                order_status,
                currency_code,
                order_total_paise,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, orders)

        # Save order items.
        connection.executemany("""
            INSERT OR IGNORE INTO order_item
            (
                order_item_id,
                order_id,
                product_id,
                quantity,
                unit_price_paise,
                line_total_paise
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, order_items)

        # Verify order totals against their items.
        mismatched_totals = connection.execute("""
            SELECT COUNT(*)
            FROM customer_order AS o
            WHERE o.order_total_paise != (
                SELECT COALESCE(SUM(oi.line_total_paise), 0)
                FROM order_item AS oi
                WHERE oi.order_id = o.order_id
            )
        """).fetchone()[0]

        saved_orders = connection.execute(
            "SELECT COUNT(*) FROM customer_order"
        ).fetchone()[0]

        saved_items = connection.execute(
            "SELECT COUNT(*) FROM order_item"
        ).fetchone()[0]

        if mismatched_totals:
            raise ValueError(
                f"Found {mismatched_totals} orders with incorrect totals."
            )

    print("\nORDER GENERATION SUMMARY")
    print("========================")
    print(f"Generated orders: {len(orders)}")
    print(f"Generated order items: {len(order_items)}")
    print(f"Orders in database: {saved_orders}")
    print(f"Order items in database: {saved_items}")
    print(f"Orders with incorrect totals: {mismatched_totals}")


if __name__ == "__main__":
    save_orders()
