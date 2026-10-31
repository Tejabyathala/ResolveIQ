import sys
from pathlib import Path
from collections import Counter
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.engine.sla_engine import (
    calculate_deadline,
    determine_clock_status,
    get_sla_targets,
)

rules = load_business_rules()

reference_datetime = datetime.fromisoformat(
    rules["generation"]["reference_datetime"].replace("Z", "+00:00")
)

errors = []

with get_connection() as connection:

    rows = connection.execute("""
        SELECT
            s.sla_clock_id,
            s.complaint_id,
            s.clock_type,
            s.started_at,
            s.target_minutes,
            s.deadline_at,
            s.clock_status,
            s.total_paused_minutes,
            c.priority,
            c.created_at
        FROM sla_clock s
        JOIN complaint c ON c.complaint_id = s.complaint_id
        ORDER BY s.complaint_id, s.clock_type
    """).fetchall()

    complaint_count = connection.execute(
        "SELECT COUNT(*) FROM complaint"
    ).fetchone()[0]

    clock_counts = Counter(row[1] for row in rows)
    status_counts = Counter(row[6] for row in rows)

    for row in rows:
        (
            clock_id, complaint_id, clock_type,
            started_at, target_minutes, deadline_at,
            clock_status, paused_minutes, priority,
            complaint_created_at
        ) = row

        targets = get_sla_targets(priority, rules)

        expected_target = (
            targets["first_response_minutes"]
            if clock_type == "FIRST_RESPONSE"
            else targets["resolution_minutes"]
        )

        start = datetime.fromisoformat(started_at)
        deadline = datetime.fromisoformat(deadline_at)
        complaint_start = datetime.fromisoformat(complaint_created_at)

        if clock_type not in {"FIRST_RESPONSE", "RESOLUTION"}:
            errors.append(f"{clock_id}: invalid clock type")

        if target_minutes != expected_target:
            errors.append(f"{clock_id}: incorrect SLA target")

        if start != complaint_start:
            errors.append(f"{clock_id}: incorrect start timestamp")

        expected_deadline = calculate_deadline(start, expected_target)

        if deadline != expected_deadline:
            errors.append(f"{clock_id}: incorrect deadline")

        expected_status = determine_clock_status(
            deadline,
            reference_datetime
        )

        if clock_status != expected_status:
            errors.append(f"{clock_id}: incorrect clock status")

        if paused_minutes != 0:
            errors.append(f"{clock_id}: unexpected paused minutes")

    incorrect_clock_counts = sum(
        1 for count in clock_counts.values() if count != 2
    )

    missing_complaints = complaint_count - len(clock_counts)

    print("SLA VALIDATION")
    print("==============")
    print("Total complaints:", complaint_count)
    print("Total SLA clocks:", len(rows))
    print("Complaints without exactly two clocks:", incorrect_clock_counts)
    print("Complaints without SLA clocks:", missing_complaints)
    print("Incorrect targets/deadlines/statuses:", len(errors))

    print("\nSLA STATUS DISTRIBUTION")
    print("=======================")

    for status, count in sorted(status_counts.items()):
        print(f"{status}: {count}")

    print("\nVALIDATION ERRORS:", len(errors))

    if errors:
        for error in errors[:20]:
            print(error)
    else:
        print("All SLA validations passed.")

if errors or len(rows) != complaint_count * 2:
    raise SystemExit(1)