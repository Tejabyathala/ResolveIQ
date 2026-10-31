from collections import Counter
from datetime import datetime

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.engine.sla_engine import (
    calculate_deadline,
    determine_clock_status,
    get_sla_targets,
)


def generate_sla_clocks():

    rules = load_business_rules()

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    sla_records = []

    with get_connection() as connection:

        complaints = connection.execute("""
            SELECT complaint_id, priority, created_at
            FROM complaint
            ORDER BY complaint_id
        """).fetchall()

        if not complaints:
            raise ValueError("No complaints found.")

        existing_count = connection.execute("""
            SELECT COUNT(*) FROM sla_clock
        """).fetchone()[0]

        if existing_count > 0:
            raise ValueError(
                f"SLA clocks already exist ({existing_count}). "
                "Do not generate duplicates."
            )

        for complaint_id, priority, created_at in complaints:

            if not priority:
                raise ValueError(
                    f"Complaint {complaint_id} has no priority."
                )

            started_at = datetime.fromisoformat(created_at)

            targets = get_sla_targets(priority, rules)

            clock_types = {
                "FIRST_RESPONSE": targets["first_response_minutes"],
                "RESOLUTION": targets["resolution_minutes"],
            }

            for clock_type, target_minutes in clock_types.items():

                deadline_at = calculate_deadline(
                    started_at,
                    target_minutes
                )

                clock_status = determine_clock_status(
                    deadline_at,
                    reference_datetime
                )

                suffix = "FR" if clock_type == "FIRST_RESPONSE" else "RS"

                sla_clock_id = f"SLA-{complaint_id}-{suffix}"

                sla_records.append((
                    sla_clock_id,
                    complaint_id,
                    clock_type,
                    started_at.isoformat(),
                    target_minutes,
                    deadline_at.isoformat(),
                    None,
                    clock_status,
                    0,
                ))

        connection.executemany("""
            INSERT INTO sla_clock (
                sla_clock_id,
                complaint_id,
                clock_type,
                started_at,
                target_minutes,
                deadline_at,
                stopped_at,
                clock_status,
                total_paused_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sla_records)

        total_clocks = connection.execute("""
            SELECT COUNT(*) FROM sla_clock
        """).fetchone()[0]

        if total_clocks != len(complaints) * 2:
            raise ValueError("SLA clock count validation failed.")

        status_counts = Counter(
            record[7] for record in sla_records
        )

        priority_counts = Counter(
            record[2] for record in sla_records
        )

    print("SLA GENERATION SUMMARY")
    print("======================")
    print("Complaints processed:", len(complaints))
    print("SLA clocks generated:", len(sla_records))
    print("First-response clocks:", priority_counts["FIRST_RESPONSE"])
    print("Resolution clocks:", priority_counts["RESOLUTION"])

    print("\nSLA CLOCK STATUS")
    print("================")

    for status, count in sorted(status_counts.items()):
        print(f"{status}: {count}")


if __name__ == "__main__":
    generate_sla_clocks()