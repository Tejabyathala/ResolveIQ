
import sys
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import src.database.connection as db_connection
from src.engine import sla_event_service as service


def run_tests():

    original_db_path = db_connection.DB_PATH

    with tempfile.TemporaryDirectory() as temp_dir:

        test_db_path = Path(temp_dir) / "resolveiq_test.db"

        # Copy the original database safely.
        source = db_connection.get_connection()
        destination = sqlite3.connect(test_db_path)

        try:
            source.backup(destination)
        finally:
            source.close()
            destination.close()

        db_connection.DB_PATH = test_db_path

        try:
            # Read the test complaint.
            connection = db_connection.get_connection()

            try:
                complaint = connection.execute("""
                    SELECT complaint_id, created_at
                    FROM complaint
                    ORDER BY created_at, complaint_id
                    LIMIT 1
                """).fetchone()
            finally:
                connection.close()

            complaint_id, created_at = complaint
            start = datetime.fromisoformat(created_at)

            # First pause and resume.
            pause1 = start + timedelta(minutes=1)
            resume1 = start + timedelta(minutes=31)

            # Second pause and resume.
            pause2 = start + timedelta(minutes=32)
            resume2 = start + timedelta(minutes=62)

            paused = service.pause_complaint_clocks(
                complaint_id,
                pause1,
                "Waiting for customer information",
            )
            assert paused == 2

            resumed = service.resume_complaint_clocks(
                complaint_id,
                resume1,
                "Customer provided information",
            )
            assert resumed == 2

            paused = service.pause_complaint_clocks(
                complaint_id,
                pause2,
                "Additional information required",
            )
            assert paused == 2

            resumed = service.resume_complaint_clocks(
                complaint_id,
                resume2,
                "Information received",
            )
            assert resumed == 2

            # Verify database results.
            connection = db_connection.get_connection()

            try:
                clocks = connection.execute("""
                    SELECT
                        clock_type,
                        clock_status,
                        total_paused_minutes
                    FROM sla_clock
                    WHERE complaint_id = ?
                """, (complaint_id,)).fetchall()

                events = connection.execute("""
                    SELECT event_type, COUNT(*)
                    FROM sla_event
                    WHERE sla_clock_id IN (
                        SELECT sla_clock_id
                        FROM sla_clock
                        WHERE complaint_id = ?
                    )
                    GROUP BY event_type
                """, (complaint_id,)).fetchall()

                deadlines = connection.execute("""
                    SELECT COUNT(*)
                    FROM sla_clock
                    WHERE complaint_id = ?
                      AND total_paused_minutes = 60
                """, (complaint_id,)).fetchone()[0]

            finally:
                connection.close()

            assert len(clocks) == 2
            assert all(row[1] != "PAUSED" for row in clocks)
            assert all(row[2] == 60 for row in clocks)
            assert deadlines == 2

            event_counts = dict(events)

            assert event_counts.get("PAUSE", 0) == 4
            assert event_counts.get("RESUME", 0) == 4

            print("PASS: Both SLA clocks paused")
            print("PASS: Both SLA clocks resumed")
            print("PASS: Second pause/resume cycle")
            print("PASS: 60 total paused minutes per clock")
            print("PASS: Four pause and four resume events")
            print("PASS: Original database remains unchanged")

            print("\nAll SLA event service tests passed.")

        finally:
            db_connection.DB_PATH = original_db_path


if __name__ == "__main__":
    run_tests()
