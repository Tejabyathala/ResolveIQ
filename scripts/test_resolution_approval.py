
import sys
import tempfile

from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import connection as db_connection
from src.database.initialize import initialize_database
from src.engine.resolution_service import (
    propose_resolution,
    approve_resolution,
)


def run_tests():
    original_db_path = db_connection.DB_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        db_connection.DB_PATH = Path(temp_dir) / "approval_test.db"

        try:
            initialize_database()

            with closing(db_connection.get_connection()) as connection:

                connection.execute("""
                    INSERT INTO customer (
                        customer_id, full_name, email, phone,
                        is_vulnerable, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "CUS-TEST-001",
                    "Test Customer",
                    "approval@example.com",
                    "9000000001",
                    0,
                    "2026-01-01T00:00:00+00:00",
                ))

                connection.execute("""
                    INSERT INTO product (
                        product_id, product_name, product_category,
                        unit_price_paise, is_safety_critical,
                        is_active, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "PRD-TEST-001",
                    "Test Product",
                    "Electronics",
                    500000,
                    0,
                    1,
                    "2026-01-01T00:00:00+00:00",
                ))

                connection.execute("""
                    INSERT INTO category (
                        category_id, category_name,
                        description, is_active
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    "CAT-009",
                    "CUSTOMER_SERVICE",
                    "Customer service complaints",
                    1,
                ))

                                # Insert the required team.
                connection.execute("""
                    INSERT INTO team (
                        team_id, team_name, description, is_active
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    "TEAM-001",
                    "TEST_TEAM",
                    "Temporary test team",
                    1,
                ))

                # Insert the required approver role.
                connection.execute("""
                    INSERT INTO role (
                        role_id, role_name, description
                    )
                    VALUES (?, ?, ?)
                """, (
                    "ROLE-003",
                    "APPROVER",
                    "Can approve resolutions",
                ))

                # Insert an active approver.
                connection.execute("""
                    INSERT INTO agent (
                        agent_id, team_id, role_id,
                        display_name, email, is_active,
                        capacity_weight
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "AGT-TEST-001",
                    "TEAM-001",
                    "ROLE-003",
                    "Test Approver",
                    "approver@example.com",
                    1,
                    1,
                ))
                # Insert complaint.
                connection.execute("""
                    INSERT INTO complaint (
                        complaint_id, customer_id, order_id,
                        product_id, category_id, priority_rule_id,
                        subject, description, channel, sentiment,
                        severity, priority, is_repeat,
                        repeat_of_complaint_id, current_status,
                        created_at, closed_at
                    )
                    VALUES (
                        ?, ?, NULL, ?, ?, NULL,
                        ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL
                    )
                """, (
                    "CMP-TEST-001",
                    "CUS-TEST-001",
                    "PRD-TEST-001",
                    "CAT-009",
                    "Test complaint",
                    "Testing approval",
                    "EMAIL",
                    "NEGATIVE",
                    "MEDIUM",
                    "P2",
                    0,
                    "IN_PROGRESS",
                    "2026-10-20T00:00:00+00:00",
                ))

                # Insert two SLA clocks.
                connection.executemany("""
                    INSERT INTO sla_clock (
                        sla_clock_id, complaint_id, clock_type,
                        started_at, target_minutes, deadline_at,
                        stopped_at, clock_status,
                        total_paused_minutes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    (
                        "SLA-TEST-FR",
                        "CMP-TEST-001",
                        "FIRST_RESPONSE",
                        "2026-10-20T00:00:00+00:00",
                        60,
                        "2026-10-22T00:00:00+00:00",
                        None,
                        "RUNNING",
                        0,
                    ),
                    (
                        "SLA-TEST-RS",
                        "CMP-TEST-001",
                        "RESOLUTION",
                        "2026-10-20T00:00:00+00:00",
                        1440,
                        "2026-10-22T00:00:00+00:00",
                        None,
                        "RUNNING",
                        0,
                    ),
                ])

                connection.commit()

            # Propose a high-value refund.
            proposal_time = datetime(
                2026, 10, 21, 10, 0,
                tzinfo=timezone.utc,
            )

            proposal = propose_resolution(
                "CMP-TEST-001",
                "REFUND",
                "Refund requires approval.",
                proposal_time,
                refund_amount_paise=1000000,
            )

            assert proposal["approval_required"] is True

            # Approve the resolution.
            approval_time = datetime(
                2026, 10, 21, 11, 0,
                tzinfo=timezone.utc,
            )

            result = approve_resolution(
                proposal["resolution_id"],
                "AGT-TEST-001",
                approval_time,
            )

            assert result["resolution_status"] == "APPROVED"
            assert result["complaint_status"] == "IN_PROGRESS"

            # Verify database updates.
            with closing(db_connection.get_connection()) as connection:

                resolution = connection.execute("""
                    SELECT resolution_status, approved_by_agent_id
                    FROM resolution
                    WHERE resolution_id = ?
                """, (proposal["resolution_id"],)).fetchone()

                complaint_status = connection.execute("""
                    SELECT current_status
                    FROM complaint
                    WHERE complaint_id = ?
                """, ("CMP-TEST-001",)).fetchone()[0]

                clocks = connection.execute("""
                    SELECT clock_status, total_paused_minutes
                    FROM sla_clock
                    WHERE complaint_id = ?
                """, ("CMP-TEST-001",)).fetchall()

            assert resolution == ("APPROVED", "AGT-TEST-001")
            assert complaint_status == "IN_PROGRESS"
            assert len(clocks) == 2
            assert all(clock[0] == "RUNNING" for clock in clocks)
            assert all(clock[1] == 60 for clock in clocks)

            print("Resolution approval test passed.")
            print("Resolution:", resolution)
            print("Complaint status:", complaint_status)
            print("SLA clocks resumed:", len(clocks))
            print("Paused minutes per clock:", clocks[0][1])

        finally:
            db_connection.DB_PATH = original_db_path


if __name__ == "__main__":
    run_tests()
