
import random

from datetime import datetime, timedelta


ORDER_STATUSES = [
    "PLACED",
    "SHIPPED",
    "DELIVERED",
    "CANCELLED",
    "RETURNED",
]


def generate_orders(customers, products, count, seed, reference_datetime):
    rng = random.Random(seed + 1)

    orders = []
    order_items = []

    year = reference_datetime.year

    for number in range(1, count + 1):
        order_id = f"ORD-{year}-{number:06d}"

        customer = rng.choice(customers)
        customer_id = customer["customer_id"]

        customer_created_at = datetime.fromisoformat(
        customer["created_at"]
        )

        year_start = reference_datetime.replace(
        month=1, day=1, hour=0, minute=0, second=0, microsecond=0
        )

        earliest_order_date = max(year_start, customer_created_at)

        available_minutes = int(
        (reference_datetime - earliest_order_date).total_seconds() // 60
        )

        order_datetime = earliest_order_date + timedelta(
        minutes=rng.randint(0, available_minutes)
        )

        order_date = order_datetime.date()
        order_status = rng.choices(
            ORDER_STATUSES,
            weights=[10, 15, 55, 10, 10],
            k=1,
        )[0]

        # Select between 1 and 5 distinct products.
        item_count = rng.randint(1, 5)
        selected_products = rng.sample(
            products,
            min(item_count, len(products)),
        )

        order_total_paise = 0

        for item_number, product in enumerate(selected_products, start=1):
            quantity = rng.randint(1, 5)
            unit_price_paise = product["unit_price_paise"]

            line_total_paise = quantity * unit_price_paise
            order_total_paise += line_total_paise

            order_items.append((
                f"OIT-{len(order_items) + 1:06d}",
                order_id,
                product["product_id"],
                quantity,
                unit_price_paise,
                line_total_paise,
            ))

        orders.append((
            order_id,
            customer_id,
            order_date.isoformat(),
            order_status,
            "INR",
            order_total_paise,
            reference_datetime.isoformat(),
        ))

    return orders, order_items


if __name__ == "__main__":
    print("Order generator module loaded successfully.")
