
import random
from datetime import timedelta
from src.database.config_loader import load_business_rules


FIRST_NAMES = [
    "Aarav", "Aditya", "Ananya", "Arjun", "Diya",
    "Ishaan", "Kavya", "Meera", "Rahul", "Riya",
    "Sai", "Sneha", "Teja", "Varun", "Vikram",
]

LAST_NAMES = [
    "Sharma", "Reddy", "Kumar", "Patel", "Rao",
    "Verma", "Gupta", "Singh", "Nair", "Das",
    "Mehta", "Iyer", "Joshi", "Mishra", "Naidu",
]


def generate_customers(count, seed, reference_datetime):
    rng = random.Random(seed)
    customers = []

    for number in range(1, count + 1):
        first_name = rng.choice(FIRST_NAMES)
        last_name = rng.choice(LAST_NAMES)

        full_name = f"{first_name} {last_name}"
        email = f"customer{number:06d}@resolveiq.local"

        # Generate unique synthetic phone numbers.
        phone = f"9{number:09d}"

        is_vulnerable = 1 if rng.random() < 0.05 else 0

        # Customers are created within the 365 days before
        # the fixed reference datetime.
        days_ago = rng.randint(0, 365)
        created_at = reference_datetime - timedelta(days=days_ago)

        customers.append((
            f"CUS-{number:06d}",
            full_name,
            email,
            phone,
            is_vulnerable,
            created_at.isoformat(),
        ))

    return customers


if __name__ == "__main__":
    rules = load_business_rules()

    count = rules["generation"]["scale"]["customers"]
    seed = rules["generation"]["seed"]

    from datetime import datetime

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    customers = generate_customers(
        count,
        seed,
        reference_datetime,
    )

    print(f"Generated customers: {len(customers)}")
    print("First customer:", customers[0])
    print("Last customer:", customers[-1])
