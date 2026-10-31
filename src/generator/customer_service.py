
from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.generator.customer_generator import generate_customers

from datetime import datetime


def save_customers():
    rules = load_business_rules()

    count = rules["generation"]["scale"]["customers"]
    seed = rules["generation"]["seed"]

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    customers = generate_customers(
        count,
        seed,
        reference_datetime,
    )

    with get_connection() as connection:
        connection.executemany("""
            INSERT OR IGNORE INTO customer
            (
                customer_id,
                full_name,
                email,
                phone,
                is_vulnerable,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, customers)

        total = connection.execute(
            "SELECT COUNT(*) FROM customer"
        ).fetchone()[0]

    print(f"Generated customers: {len(customers)}")
    print(f"Customers stored in database: {total}")


if __name__ == "__main__":
    save_customers()
