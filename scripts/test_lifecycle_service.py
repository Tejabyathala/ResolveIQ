
import sys
import sqlite3
import tempfile

from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import connection as db_connection
from src.engine.lifecycle_service import transition_complaint


def run_tests():
    original_db_path = db_connection.DB_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = Path(temp_dir) / "resolveiq_test.db"

        # Copy the original database.
        source = db_connection.get_connection()
        destination = sqlite3.connect(test_db_path)

        try:
            source.backup(destination)
        finally:
            source.close()
            destination.close()

        # Switch to the temporary database.
        db_connection.DB_PATH = test_db_path

        try:
            connection = db_connection.get_connection()

            try:
                # Find one assigned complaint.
                complaint = connection.execute("""
                    SELECT complaint_id
                    FROM complaint
                    WHERE current_status = 'ASSIGNED'
                    ORDER BY complaint_id
                    LIMIT 1
                """).fetchone()

                if complaint is None:
                    raise RuntimeError("No ASSIGNED complaint found.")

                complaint_id = complaint[0]

                # Set the initial assignment event to a suitable
                # timestamp in the temporary test database.
                test_start = "2026-10-21T20:00:00+00:00"

                cursor = connection.execute("""
                    UPDATE complaint_status_event
                    SET changed_at = ?
                    WHERE complaint_id = ?
                    AND to_status = 'ASSIGNED'
                """, (test_start, complaint_id))

                if cursor.rowcount == 0:
                    raise RuntimeError(
                        "Initial ASSIGNED status event not found."
                    )

                # Prepare both SLA clocks for this isolated lifecycle test.
            # Give them future deadlines and RUNNING status.
                connection.execute("""
                    UPDATE sla_clock
                    SET deadline_at = '2026-10-22T00:00:00+00:00',
                    clock_status = 'RUNNING',
                    total_paused_minutes = 0
                    WHERE complaint_id = ?
                    """, (complaint_id,))

                connection.commit()

                changed_at = (
                datetime.fromisoformat(test_start)
                + timedelta(minutes=1)
            )

            finally:
                connection.close()

            # Test 1: ASSIGNED -> IN_PROGRESS
            result = transition_complaint(
                complaint_id,
                "IN_PROGRESS",
                changed_at,
                "Agent started investigation.",
            )

            assert result["previous_status"] == "ASSIGNED"
            assert result["current_status"] == "IN_PROGRESS"

            print("PASS: ASSIGNED -> IN_PROGRESS")

            # Test 2: IN_PROGRESS -> PENDING_CUSTOMER
            changed_at += timedelta(minutes=5)

            result = transition_complaint(
                complaint_id,
                "PENDING_CUSTOMER",
                changed_at,
                "Waiting for customer response.",
            )

            assert result["current_status"] == "PENDING_CUSTOMER"

            print("PASS: SLA clocks paused when entering pending status")

            # Test 3: PENDING_CUSTOMER -> IN_PROGRESS
            changed_at += timedelta(minutes=30)

            result = transition_complaint(
                complaint_id,
                "IN_PROGRESS",
                changed_at,
                "Customer provided additional information.",
            )

            assert result["current_status"] == "IN_PROGRESS"

            print("PASS: SLA clocks resumed when leaving pending status")

            # Test 4: Invalid transition
            try:
                transition_complaint(
                    complaint_id,
                    "CLOSED",
                    changed_at + timedelta(minutes=1),
                    "Invalid direct closure.",
                )

                raise AssertionError(
                    "Invalid transition was accepted."
                )

            except ValueError:
                print("PASS: Invalid transition rejected")

            # Test 5: Verify status and SLA event history.
            connection = db_connection.get_connection()

            try:
                events = connection.execute("""
                    SELECT from_status, to_status
                    FROM complaint_status_event
                    WHERE complaint_id = ?
                    ORDER BY changed_at, status_event_id
                """, (complaint_id,)).fetchall()

                assert events[-3:] == [
                    ("ASSIGNED", "IN_PROGRESS"),
                    ("IN_PROGRESS", "PENDING_CUSTOMER"),
                    ("PENDING_CUSTOMER", "IN_PROGRESS"),
                ]

                print("PASS: Status history recorded correctly")

                sla_events = connection.execute("""
                    SELECT event_type, COUNT(*)
                    FROM sla_event
                    WHERE sla_clock_id IN (
                        SELECT sla_clock_id
                        FROM sla_clock
                        WHERE complaint_id = ?
                    )
                    GROUP BY event_type
                """, (complaint_id,)).fetchall()

                sla_counts = dict(sla_events)

                assert sla_counts.get("PAUSE", 0) == 2
                assert sla_counts.get("RESUME", 0) == 2

                print("PASS: SLA event history recorded correctly")

            finally:
                connection.close()

            print("\nAll lifecycle service tests passed.")

        finally:
            # Restore the original database path.
            db_connection.DB_PATH = original_db_path


if __name__ == "__main__":
    run_tests()
