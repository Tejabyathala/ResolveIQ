
from pathlib import Path
import sqlite3
from datetime import datetime, timedelta


ROOT = Path(__file__).resolve().parents[2]

ANOMALY_DB = (
    ROOT
    / "output"
    / "with_anomalies"
    / "resolveiq_anomalies.db"
)


def detect_incorrect_order_totals(connection):
    query = """
        SELECT
            o.order_id,
            o.order_total_paise,
            COALESCE(SUM(oi.line_total_paise), 0) AS calculated_total
        FROM customer_order o
        LEFT JOIN order_item oi
            ON oi.order_id = o.order_id
        GROUP BY o.order_id
        HAVING o.order_total_paise != calculated_total
    """

    rows = connection.execute(query).fetchall()

    return [
        {
            "record_id": row[0],
            "anomaly_type": "INCORRECT_ORDER_TOTAL",
        }
        for row in rows
    ]


def detect_incorrect_item_prices(connection):
    query = """
        SELECT
            oi.order_item_id
        FROM order_item oi
        JOIN product p
            ON p.product_id = oi.product_id
        WHERE oi.unit_price_paise != p.unit_price_paise
    """

    rows = connection.execute(query).fetchall()

    return [
        {
            "record_id": row[0],
            "anomaly_type": "INCORRECT_ITEM_PRICE",
        }
        for row in rows
    ]

def detect_customer_order_mismatches(connection):
    query = """
        SELECT
            c.complaint_id
        FROM complaint c
        JOIN customer_order o
            ON o.order_id = c.order_id
        WHERE c.customer_id != o.customer_id
    """

    rows = connection.execute(query).fetchall()

    return [
        {
            "record_id": row[0],
            "anomaly_type": "CUSTOMER_ORDER_MISMATCH",
        }
        for row in rows
    ]

def detect_invalid_sla_deadlines(connection):
    rows = connection.execute(
        """
        SELECT
            sla_clock_id,
            started_at,
            target_minutes,
            deadline_at
        FROM sla_clock
        """
    ).fetchall()

    anomalies = []

    for clock_id, started_at, target_minutes, deadline_at in rows:
        try:
            started = datetime.fromisoformat(
                started_at.replace("Z", "+00:00")
            )

            deadline = datetime.fromisoformat(
                deadline_at.replace("Z", "+00:00")
            )

            expected_deadline = started + timedelta(
                minutes=target_minutes
            )

            if deadline != expected_deadline:
                anomalies.append({
                    "record_id": clock_id,
                    "anomaly_type": "INVALID_SLA_DEADLINE",
                })

        except (ValueError, TypeError):
            anomalies.append({
                "record_id": clock_id,
                "anomaly_type": "INVALID_SLA_DEADLINE",
            })

    return anomalies

def detect_wrong_team_assignments(connection):
    import yaml

    rules_path = ROOT / "config" / "business_rules.yaml"

    with open(rules_path, "r", encoding="utf-8") as file:
        rules = yaml.safe_load(file)

    routing = rules["routing"]

    rows = connection.execute(
        """
        SELECT
            a.assignment_id,
            a.team_id,
            c.category_id
        FROM assignment a
        JOIN complaint c
            ON c.complaint_id = a.complaint_id
        WHERE a.is_current = 1
        """
    ).fetchall()

    anomalies = []

    for assignment_id, actual_team_id, category_id in rows:
        expected_team_name = routing.get(category_id)

        if expected_team_name is None:
            continue

        expected_team = connection.execute(
            """
            SELECT team_id
            FROM team
            WHERE team_name = ?
            """,
            (expected_team_name,),
        ).fetchone()

        if expected_team is None:
            continue

        if actual_team_id != expected_team[0]:
            anomalies.append({
                "record_id": assignment_id,
                "anomaly_type": "WRONG_TEAM_ASSIGNMENT",
            })

    return anomalies

def detect_all_anomalies():
    connection = sqlite3.connect(ANOMALY_DB)

    try:
        detected = []

        detectors = [
            detect_incorrect_order_totals,
            detect_incorrect_item_prices,
            detect_customer_order_mismatches,
            detect_invalid_sla_deadlines,
            detect_wrong_team_assignments,
        ]

        for detector in detectors:
            detected.extend(detector(connection))

        return detected

    finally:
        connection.close()
