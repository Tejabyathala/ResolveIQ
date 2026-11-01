
import csv
import random
import shutil
import sqlite3
from pathlib import Path
from src.database.config_loader import load_business_rules

ROOT = Path(__file__).resolve().parents[2]

CLEAN_DB = ROOT / "output" / "clean" / "resolveiq_clean.db"
ANOMALY_DB = ROOT / "output" / "with_anomalies" / "resolveiq_anomalies.db"
GROUND_TRUTH = ROOT / "output" / "ground_truth" / "ground_truth.csv"

SEED = 20261022
ANOMALIES_PER_TYPE = 20


def inject_anomalies():
    if not CLEAN_DB.exists():
        raise FileNotFoundError(CLEAN_DB)

    if not GROUND_TRUTH.parent.exists():
        GROUND_TRUTH.parent.mkdir(parents=True)

    # Always recreate the anomaly database from the clean baseline.
    shutil.copy2(CLEAN_DB, ANOMALY_DB)

    rng = random.Random(SEED)
    connection = sqlite3.connect(ANOMALY_DB)

    ground_truth = []

    try:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            # 1. Incorrect order totals.
            orders = connection.execute(
                """
                SELECT order_id, order_total_paise
                FROM customer_order
                ORDER BY order_id
                """
            ).fetchall()

            selected = rng.sample(orders, ANOMALIES_PER_TYPE)

            for order_id, total in selected:
                connection.execute(
                    """
                    UPDATE customer_order
                    SET order_total_paise = ?
                    WHERE order_id = ?
                    """,
                    (total + 100, order_id),
                )

                ground_truth.append((
                    order_id,
                    "INCORRECT_ORDER_TOTAL",
                    "customer_order",
                    "HIGH",
                ))

            # 2. Incorrect item prices.
            
            items = connection.execute(
                """
                SELECT order_item_id, order_id, unit_price_paise,
                       quantity, line_total_paise
                FROM order_item
                ORDER BY order_item_id
                """
            ).fetchall()

            selected = rng.sample(items, ANOMALIES_PER_TYPE)

            for item_id, order_id, price, quantity, old_line_total in selected:
                new_line_total = quantity * (price + 100)
                difference = new_line_total - old_line_total

                connection.execute(
                    """
                    UPDATE order_item
                    SET unit_price_paise = ?,
                        line_total_paise = ?
                    WHERE order_item_id = ?
                    """,
                    (price + 100, new_line_total, item_id),
                )

                connection.execute(
                    """
                    UPDATE customer_order
                    SET order_total_paise = order_total_paise + ?
                    WHERE order_id = ?
                    """,
                    (difference, order_id),
                )

                ground_truth.append((
                    item_id,
                    "INCORRECT_ITEM_PRICE",
                    "order_item",
                    "MEDIUM",
                ))

            # 3. Customer/order relationship mismatch.
            complaints = connection.execute(
                """
                SELECT complaint_id, customer_id, order_id
                FROM complaint
                WHERE order_id IS NOT NULL
                ORDER BY complaint_id
                """
            ).fetchall()

            selected = rng.sample(
                complaints,
                ANOMALIES_PER_TYPE,
            )

            for complaint_id, customer_id, order_id in selected:
                other_customer = connection.execute(
                    """
                    SELECT customer_id
                    FROM customer
                    WHERE customer_id != ?
                    ORDER BY customer_id
                    LIMIT 1
                    """,
                    (customer_id,),
                ).fetchone()[0]

                connection.execute(
                    """
                    UPDATE complaint
                    SET customer_id = ?
                    WHERE complaint_id = ?
                    """,
                    (other_customer, complaint_id),
                )

                ground_truth.append((
                    complaint_id,
                    "CUSTOMER_ORDER_MISMATCH",
                    "complaint",
                    "HIGH",
                ))

            # 4. Incorrect SLA deadlines.
            clocks = connection.execute(
                """
                SELECT sla_clock_id, deadline_at
                FROM sla_clock
                ORDER BY sla_clock_id
                """
            ).fetchall()

            selected = rng.sample(clocks, ANOMALIES_PER_TYPE)

            for clock_id, deadline in selected:
                connection.execute(
                    """
                    UPDATE sla_clock
                    SET deadline_at = ?
                    WHERE sla_clock_id = ?
                    """,
                    (deadline + " ", clock_id),
                )

                ground_truth.append((
                    clock_id,
                    "INVALID_SLA_DEADLINE",
                    "sla_clock",
                    "HIGH",
                ))

            
            # 5. Wrong team assignment.
            rules = load_business_rules()
            routing = rules["routing"]

            assignments = connection.execute(
                """
                SELECT a.assignment_id, c.category_id, a.team_id
                FROM assignment a
                JOIN complaint c
                  ON c.complaint_id = a.complaint_id
                WHERE a.is_current = 1
                ORDER BY a.assignment_id
                """
            ).fetchall()

            selected = rng.sample(
                assignments,
                ANOMALIES_PER_TYPE,
            )

            for assignment_id, category_id, current_team in selected:
                expected_team_name = routing.get(category_id)

                if expected_team_name is None:
                    continue

                correct_team = connection.execute(
                    """
                    SELECT team_id
                    FROM team
                    WHERE team_name = ?
                    """,
                    (expected_team_name,),
                ).fetchone()

                if correct_team is None:
                    continue

                if correct_team[0] == current_team:
                    wrong_team = connection.execute(
                        """
                        SELECT team_id
                        FROM team
                        WHERE team_id != ?
                        ORDER BY team_id
                        LIMIT 1
                        """,
                        (current_team,),
                    ).fetchone()

                    if wrong_team is None:
                        continue

                    connection.execute(
                        """
                        UPDATE assignment
                        SET team_id = ?
                        WHERE assignment_id = ?
                        """,
                        (wrong_team[0], assignment_id),
                    )

                    ground_truth.append((
                        assignment_id,
                        "WRONG_TEAM_ASSIGNMENT",
                        "assignment",
                        "HIGH",
                    ))


        with GROUND_TRUTH.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.writer(file)

            writer.writerow([
                "record_id",
                "anomaly_type",
                "table_name",
                "severity",
            ])

            writer.writerows(ground_truth)

        print("ANOMALIES INJECTED:", len(ground_truth))
        print("GROUND TRUTH:", GROUND_TRUTH)
        print("ANOMALY DATABASE:", ANOMALY_DB)

    finally:
        connection.close()


if __name__ == "__main__":
    inject_anomalies()
