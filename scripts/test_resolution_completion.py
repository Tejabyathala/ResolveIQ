
import sys
import tempfile

from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import connection as db_connection
from src.database.initialize import initialize_database

from src.engine.resolution_service import (
    propose_resolution,
    approve_resolution,
    complete_resolution,
)


def run_test():
    original_db_path = db_connection.DB_PATH
    connection = None

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_connection.DB_PATH = Path(temp_dir) / "test.db"

            initialize_database()

            connection = db_connection.get_connection()

            try:
                with connection:
                    connection.execute("""
                        INSERT INTO team (team_id, team_name)
                        VALUES ('TEAM-TEST', 'TEST_TEAM')
                    """)

                    connection.execute("""
                        INSERT INTO role (role_id, role_name)
                        VALUES ('ROLE-003', 'APPROVER')
                    """)

                    connection.execute("""
                        INSERT INTO agent (
                            agent_id, team_id, role_id,
                            display_name, email, is_active,
                            capacity_weight
                        )
                        VALUES (
                            'AGT-TEST-001', 'TEAM-TEST', 'ROLE-003',
                            'Test Approver', 'approver@test.com',
                            1, 1
                        )
                    """)

                    connection.execute("""
                        INSERT INTO customer (
                            customer_id, full_name, email,
                            phone, is_vulnerable, created_at
                        )
                        VALUES (
                            'CUS-TEST-001', 'Test Customer',
                            'customer@test.com', '9999999999',
                            0, '2026-01-01T00:00:00+00:00'
                        )
                    """)

                    connection.execute("""
                        INSERT INTO category (
                            category_id, category_name, description
                        )
                        VALUES (
                            'CAT-009', 'CUSTOMER_SERVICE', 'Test category'
                        )
                    """)

                    connection.execute("""
                        INSERT INTO complaint (
                            complaint_id, customer_id, category_id,
                            subject, description, channel,
                            sentiment, severity, priority,
                            current_status, created_at
                        )
                        VALUES (
                            'CMP-TEST-001', 'CUS-TEST-001',
                            'CAT-009', 'Test complaint',
                            'Test description', 'EMAIL',
                            'NEUTRAL', 'LOW', 'P4',
                            'IN_PROGRESS',
                            '2026-10-20T00:00:00+00:00'
                        )
                    """)

                    for clock_type in (
                        "FIRST_RESPONSE",
                        "RESOLUTION",
                    ):
                        connection.execute("""
                            INSERT INTO sla_clock (
                                sla_clock_id, complaint_id, clock_type,
                                started_at, deadline_at,
                                target_minutes, total_paused_minutes,
                                clock_status
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            f"SLA-CMP-TEST-001-{clock_type}",
                            "CMP-TEST-001",
                            clock_type,
                            "2026-10-20T00:00:00+00:00",
                            "2026-10-23T00:00:00+00:00",
                            1440,
                            0,
                            "RUNNING",
                        ))
            finally:
                connection.close()
                connection = None

            # Test 1: Approval-free completion.
            first_time = datetime(
                2026, 10, 21, 1, 0, tzinfo=timezone.utc
            )

            result = propose_resolution(
                "CMP-TEST-001",
                "INFORMATION",
                "Provided the requested information.",
                first_time,
            )

            completion_time = first_time + timedelta(minutes=30)

            completed = complete_resolution(
                result["resolution_id"],
                completion_time,
            )

            assert completed["resolution_status"] == "COMPLETED"
            assert completed["complaint_status"] == "RESOLVED"

            connection = db_connection.get_connection()

            try:
                resolution = connection.execute("""
                    SELECT resolution_status, resolved_at
                    FROM resolution
                    WHERE resolution_id = ?
                """, (result["resolution_id"],)).fetchone()

                complaint_status = connection.execute("""
                    SELECT current_status
                    FROM complaint
                    WHERE complaint_id = 'CMP-TEST-001'
                """).fetchone()[0]

                clocks = connection.execute("""
                    SELECT clock_status
                    FROM sla_clock
                    WHERE complaint_id = 'CMP-TEST-001'
                """).fetchall()

                stop_events = connection.execute("""
                    SELECT COUNT(*)
                    FROM sla_event
                    WHERE event_type = 'STOP'
                """).fetchone()[0]

            finally:
                connection.close()
                connection = None

            assert resolution[0] == "COMPLETED"
            assert resolution[1] == completion_time.isoformat()
            assert complaint_status == "RESOLVED"
            assert all(clock[0] == "STOPPED" for clock in clocks)
            assert stop_events == 2

            print("Approval-free completion test passed.")

            # Test 2: Approval-required completion.
            connection = db_connection.get_connection()

            try:
                with connection:
                    connection.execute("""
                        UPDATE complaint
                        SET current_status = 'IN_PROGRESS'
                        WHERE complaint_id = 'CMP-TEST-001'
                    """)

                    connection.execute("""
                        UPDATE sla_clock
                        SET clock_status = 'RUNNING'
                        WHERE complaint_id = 'CMP-TEST-001'
                    """)
            finally:
                connection.close()
                connection = None

            second_time = datetime(
                2026, 10, 21, 2, 0, tzinfo=timezone.utc
            )

            result = propose_resolution(
                "CMP-TEST-001",
                "REFUND",
                "Refund requires approval.",
                second_time,
                refund_amount_paise=1500000,
            )

            assert result["approval_required"] is True

            approved_time = second_time + timedelta(minutes=10)

            approve_resolution(
                result["resolution_id"],
                "AGT-TEST-001",
                approved_time,
            )

            completion_time = approved_time + timedelta(minutes=10)

            completed = complete_resolution(
                result["resolution_id"],
                completion_time,
                actor_agent_id="AGT-TEST-001",
            )

            assert completed["resolution_status"] == "COMPLETED"

            connection = db_connection.get_connection()

            try:
                status = connection.execute("""
                    SELECT resolution_status, resolved_at
                    FROM resolution
                    WHERE resolution_id = ?
                """, (result["resolution_id"],)).fetchone()

                clocks = connection.execute("""
                    SELECT clock_status
                    FROM sla_clock
                    WHERE complaint_id = 'CMP-TEST-001'
                """).fetchall()

            finally:
                connection.close()
                connection = None

            assert status[0] == "COMPLETED"
            assert status[1] == completion_time.isoformat()
            assert all(clock[0] == "STOPPED" for clock in clocks)

            print("Approved resolution completion test passed.")
            print("\nAll resolution completion tests passed.")

    finally:
        if connection is not None:
            connection.close()

        db_connection.DB_PATH = original_db_path


if __name__ == "__main__":
    run_test()
