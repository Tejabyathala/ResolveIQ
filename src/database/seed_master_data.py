
import json
import random
from datetime import datetime
from src.database.connection import get_connection
from src.database.config_loader import load_business_rules


def seed_categories(connection):
    categories = [
        ("CAT-001", "PRODUCT_SAFETY", "Product safety and potential hazards"),
        ("CAT-002", "PRODUCT_QUALITY", "Defective or poor-quality products"),
        ("CAT-003", "DELIVERY_DELAY", "Late or delayed deliveries"),
        ("CAT-004", "DAMAGED_DELIVERY", "Products damaged during delivery"),
        ("CAT-005", "PAYMENT_ISSUE", "Payment and billing problems"),
        ("CAT-006", "REFUND_REQUEST", "Refund-related complaints"),
        ("CAT-007", "ORDER_CANCELLATION", "Order cancellation requests"),
        ("CAT-008", "ACCOUNT_ACCESS", "Account login and access problems"),
        ("CAT-009", "CUSTOMER_SERVICE", "Customer service experience"),
        ("CAT-010", "GENERAL_ENQUIRY", "General questions and enquiries"),
    ]

    connection.executemany("""
        INSERT OR IGNORE INTO category
        (category_id, category_name, description, is_active)
        VALUES (?, ?, ?, 1)
    """, categories)


def seed_teams(connection, routing):
    team_names = list(dict.fromkeys(
        value
        for key, value in routing.items()
        if key.startswith("CAT-")
    ))

    teams = [
        (
            f"TEAM-{index:03d}",
            team_name,
            f"Handles {team_name.replace('_', ' ').lower()} cases",
            1,
        )
        for index, team_name in enumerate(team_names, start=1)
    ]

    connection.executemany("""
        INSERT OR IGNORE INTO team
        (team_id, team_name, description, is_active)
        VALUES (?, ?, ?, ?)
    """, teams)


def seed_roles(connection):
    role_names = [
        "BUSINESS_REQUESTER",
        "PROCESS_OWNER",
        "APPROVER",
        "OPERATIONS_ANALYST",
        "SYSTEM_ADMINISTRATOR",
    ]

    roles = [
        (
            f"ROLE-{index:03d}",
            role_name,
            f"ResolveIQ {role_name.replace('_', ' ').lower()} role",
        )
        for index, role_name in enumerate(role_names, start=1)
    ]

    connection.executemany("""
        INSERT OR IGNORE INTO role
        (role_id, role_name, description)
        VALUES (?, ?, ?)
    """, roles)


def seed_agents(connection):
    teams = connection.execute("""
        SELECT team_id
        FROM team
        ORDER BY team_id
    """).fetchall()

    roles = {
        name: role_id
        for role_id, name in connection.execute("""
            SELECT role_id, role_name
            FROM role
        """).fetchall()
    }

    agents = []

    for number in range(1, 51):
        team_id = teams[(number - 1) % len(teams)][0]

        if number <= 5:
            role_name = "PROCESS_OWNER"
        elif number <= 10:
            role_name = "APPROVER"
        elif number <= 48:
            role_name = "OPERATIONS_ANALYST"
        else:
            role_name = "SYSTEM_ADMINISTRATOR"

        agents.append((
            f"AGT-{number:06d}",
            team_id,
            roles[role_name],
            f"Agent {number:03d}",
            f"agent{number:03d}@resolveiq.local",
            1,
            1,
        ))

    connection.executemany("""
        INSERT OR IGNORE INTO agent
        (
            agent_id,
            team_id,
            role_id,
            display_name,
            email,
            is_active,
            capacity_weight
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, agents)



def seed_products(connection, count, seed):
    rng = random.Random(seed)

    product_categories = [
        "Electronics",
        "Home Appliances",
        "Clothing",
        "Grocery",
        "Furniture",
        "Personal Care",
        "Sports",
        "Accessories",
        "Toys",
        "Other",
    ]

    products = []

    for number in range(1, count + 1):
        product_category = rng.choice(product_categories)

        # Store monetary values as integer paise.
        unit_price_paise = rng.randint(10000, 5000000)

        # First 20 products are safety-critical.
        is_safety_critical = 1 if number <= 20 else 0

        products.append((
            f"PRD-{number:06d}",
            f"Product {number:04d}",
            product_category,
            unit_price_paise,
            is_safety_critical,
            1,
            "2026-10-22T00:00:00+00:00",
        ))

    connection.executemany("""
        INSERT OR IGNORE INTO product
        (
            product_id,
            product_name,
            product_category,
            unit_price_paise,
            is_safety_critical,
            is_active,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, products)



def seed_priority_rules(connection, rules):
    priority_config = rules["priority"]
    levels = priority_config["levels"]

    triggers = {
        "P1": "safety_or_critical",
        "P2": "high_severity_or_escalation",
        "P3": "medium_severity_default",
        "P4": "low_severity",
    }

    effective_from = rules["generation"]["reference_datetime"]

    priority_rules = []

    for priority, rank in levels.items():
        conditions = {
            "priority": priority,
            "rank": rank,
            "trigger": triggers[priority],
            "safety_override": priority_config["safety_override"],
            "high_value_threshold_paise":
                priority_config["high_value_threshold_paise"],
            "vulnerable_customer_escalation":
                priority_config["vulnerable_customer_escalation"],
            "repeat_complaint_escalation":
                priority_config["repeat_complaint_escalation"],
        }

        priority_rules.append((
            f"PR-{rank:03d}",
            f"PRIORITY_{priority}",
            1,
            priority,
            json.dumps(conditions),
            effective_from,
            None,
            1,
        ))

    connection.executemany("""
        INSERT OR IGNORE INTO priority_rule
        (
            priority_rule_id,
            rule_name,
            rule_version,
            priority,
            conditions_json,
            effective_from,
            effective_to,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, priority_rules)


def print_seed_summary(connection):
    tables = [
        "category",
        "team",
        "role",
        "agent",
        "product",
        "priority_rule",
    ]

    print("\nMASTER DATA SEED SUMMARY")
    print("========================")

    for table in tables:
        count = connection.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print(f"{table}: {count}")


def seed_master_data():
    rules = load_business_rules()

    product_count = rules["generation"]["scale"]["products"]
    seed = rules["generation"]["seed"]

    with get_connection() as connection:
        seed_categories(connection)
        seed_teams(connection, rules["routing"])
        seed_roles(connection)
        seed_agents(connection)
        seed_products(connection, product_count, seed)
        seed_priority_rules(connection, rules)

        print_seed_summary(connection)

    print("\nMaster data seeded successfully!")


if __name__ == "__main__":
    seed_master_data()
