import random
from datetime import datetime, timedelta


CHANNELS = ["EMAIL", "PHONE", "WEB", "CHAT", "SOCIAL"]

SENTIMENTS = ["POSITIVE", "NEUTRAL", "NEGATIVE"]
SENTIMENT_WEIGHTS = [10, 25, 65]

SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
SEVERITY_WEIGHTS = [20, 45, 25, 10]

COMPLAINT_TEMPLATES = {
    "CAT-001": (
        "Product safety concern",
        "Customer reported a possible safety issue with the product."
    ),
    "CAT-002": (
        "Product quality issue",
        "Customer reported a defect or quality problem."
    ),
    "CAT-003": (
        "Delivery delay",
        "Customer reported that the order has not arrived on time."
    ),
    "CAT-004": (
        "Damaged delivery",
        "Customer reported receiving a damaged product."
    ),
    "CAT-005": (
        "Payment issue",
        "Customer reported an incorrect or unsuccessful payment."
    ),
    "CAT-006": (
        "Refund request",
        "Customer requested a refund for the purchase."
    ),
    "CAT-007": (
        "Order cancellation",
        "Customer requested cancellation of the order."
    ),
    "CAT-008": (
        "Account access issue",
        "Customer reported difficulty accessing their account."
    ),
    "CAT-009": (
        "Customer service complaint",
        "Customer expressed dissatisfaction with customer service."
    ),
    "CAT-010": (
        "General enquiry",
        "Customer contacted support with a general enquiry."
    ),
}


def generate_complaints(
    customers,
    orders,
    order_items,
    categories,
    count,
    seed,
    reference_datetime
):
    rng = random.Random(seed + 2)

    complaints = []

    # Group orders by customer.
    orders_by_customer = {}

    for order in orders:
        orders_by_customer.setdefault(
            order["customer_id"], []
        ).append(order)

    # Group order items by order.
    items_by_order = {}

    for item in order_items:
        items_by_order.setdefault(
            item["order_id"], []
        ).append(item)

    category_ids = [
        category["category_id"] for category in categories
    ]

    for number in range(1, count + 1):

        complaint_id = (
            f"CMP-{reference_datetime.year}-{number:06d}"
        )
        # Find previous complaints eligible for repetition.
        repeat_candidates = []

        for previous in complaints:
            minutes_available = int(
                (reference_datetime - previous["_datetime"])
                .total_seconds() // 60
            )

            if 1 <= minutes_available <= 30 * 24 * 60:
                repeat_candidates.append(previous)

        is_repeat = 0
        repeat_of_complaint_id = None

        if repeat_candidates and rng.random() < 0.12:
            previous = rng.choice(repeat_candidates)

            customer_id = previous["customer_id"]
            category_id = previous["category_id"]

            minutes_available = int(
                (reference_datetime - previous["_datetime"])
                .total_seconds() // 60
            )

            minutes_after = rng.randint(
                1, min(30 * 24 * 60, minutes_available)
            )

            created_at = previous["_datetime"] + timedelta(
                minutes=minutes_after
            )

            is_repeat = 1
            repeat_of_complaint_id = previous["complaint_id"]

        else:
            customer = rng.choice(customers)

            customer_id = customer["customer_id"]
            category_id = rng.choice(category_ids)

            customer_created_at = datetime.fromisoformat(
                customer["created_at"]
            )

            # Complaint must occur after customer registration.
            earliest_date = max(
                reference_datetime - timedelta(days=365),
                customer_created_at,
            )

            available_minutes = int(
                (reference_datetime - earliest_date)
                .total_seconds() // 60
            )

            created_at = earliest_date + timedelta(
                minutes=rng.randint(0, available_minutes)
            )

        # Attach an order in 85% of eligible cases.
        customer_orders = orders_by_customer.get(
            customer_id, []
        )

        eligible_orders = [
            order for order in customer_orders
            if order["order_date"] <= created_at.date().isoformat()
        ]

        order_id = None
        product_id = None

        if eligible_orders and rng.random() < 0.85:
            selected_order = rng.choice(eligible_orders)
            order_id = selected_order["order_id"]

            available_items = items_by_order.get(order_id, [])

            if available_items:
                selected_item = rng.choice(available_items)
                product_id = selected_item["product_id"]

        subject, description = COMPLAINT_TEMPLATES[category_id]

        sentiment = rng.choices(
            SENTIMENTS,
            weights=SENTIMENT_WEIGHTS,
            k=1
        )[0]

        severity = rng.choices(
            SEVERITIES,
            weights=SEVERITY_WEIGHTS,
            k=1
        )[0]

        channel = rng.choice(CHANNELS)

        complaint = {
            "complaint_id": complaint_id,
            "customer_id": customer_id,
            "order_id": order_id,
            "product_id": product_id,
            "category_id": category_id,
            "priority_rule_id": None,
            "subject": subject,
            "description": description,
            "channel": channel,
            "sentiment": sentiment,
            "severity": severity,
            "priority": None,
            "is_repeat": is_repeat,
            "repeat_of_complaint_id": repeat_of_complaint_id,
            "current_status": "NEW",
            "created_at": created_at.isoformat(),
            "closed_at": None,
            "_datetime": created_at,
        }

        complaints.append(complaint)

    # Remove the internal datetime helper before returning.
    for complaint in complaints:
        complaint.pop("_datetime")

    return complaints


if __name__ == "__main__":
    print("Complaint generator module loaded successfully.")
