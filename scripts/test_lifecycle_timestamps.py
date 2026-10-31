
import sys
import sqlite3
import tempfile

from pathlib import Path
from datetime import datetime, timedelta, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import connection as db_connection
from src.engine.lifecycle_service import validate_transition_time


REFERENCE_DATETIME = datetime(
    2026, 10, 22, 0, 0, 0, tzinfo=timezone.utc
)


def run_tests():
    original_db_path = db_connection.DB_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = Path(temp_dir) / "resolveiq_timestamp_test.db"

        # Copy original database.
        source = db_connection.get_connection()
        destination = sqlite3.connect(test_db_path)

        try:
            source.backup(destination)
        finally:
            source.close()
            destination.close()

        db_connection.DB_PATH = test_db_path

        try:
            connection = db_connection.get_connection()

            try:
                complaint = connection.execute("""
                    SELECT complaint_id, created_at
                    FROM complaint
                    ORDER BY complaint_id
                    LIMIT 1
                """).fetchone()

                if complaint is None:
                    raise RuntimeError("No complaint found.")

                complaint_id = complaint[0]
                created_at = datetime.fromisoformat(complaint[1])

                # Set up a predictable status-event timestamp.
                test_event_time = (
                    REFERENCE_DATETIME - timedelta(hours=2)
                )

                connection.execute("""
                    DELETE FROM complaint_status_event
                    WHERE complaint_id = ?
                """, (complaint_id,))

                connection.execute("""
                    INSERT INTO complaint_status_event (
                        status_event_id,
                        complaint_id,
                        from_status,
                        to_status,
                        changed_at,
                        actor_agent_id,
                        reason
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "STSE-TIMESTAMP-TEST",
                    complaint_id,
                    "NEW",
                    "TRIAGED",
                    test_event_time.isoformat(),
                    None,
                    "Timestamp validation test setup.",
                ))

                connection.commit()

                # Test 1: Valid timestamp.
                valid_time = test_event_time + timedelta(minutes=1)

                validate_transition_time(
                    connection,
                    complaint_id,
                    valid_time,
                )

                print("PASS: Valid timestamp accepted")

                # Test 2: Before complaint creation.
                before_creation = created_at - timedelta(minutes=1)

                try:
                    validate_transition_time(
                        connection,
                        complaint_id,
                        before_creation,
                    )
                    raise AssertionError(
                        "Timestamp before complaint creation was accepted."
                    )
                except ValueError as error:
                    assert "before complaint creation" in str(error)

                print("PASS: Timestamp before complaint creation rejected")

                # Test 3: Before latest status event.
                before_latest_event = test_event_time - timedelta(minutes=1)

                try:
                    validate_transition_time(
                        connection,
                        complaint_id,
                        before_latest_event,
                    )
                    raise AssertionError(
                        "Out-of-order timestamp was accepted."
                    )
                except ValueError as error:
                    assert "latest status event" in str(error)

                print("PASS: Earlier status-event timestamp rejected")

                # Test 4: After reference datetime.
                future_time = REFERENCE_DATETIME + timedelta(minutes=1)

                try:
                    validate_transition_time(
                        connection,
                        complaint_id,
                        future_time,
                    )
                    raise AssertionError(
                        "Future timestamp was accepted."
                    )
                except ValueError as error:
                    assert "reference datetime" in str(error)

                print("PASS: Future timestamp rejected")

                # Test 5: Naive datetime.
                naive_time = datetime(2026, 10, 21, 22, 30)

                try:
                    validate_transition_time(
                        connection,
                        complaint_id,
                        naive_time,
                    )
                    raise AssertionError(
                        "Naive datetime was accepted."
                    )
                except ValueError as error:
                    assert "timezone information" in str(error)

                print("PASS: Timezone-naive timestamp rejected")

            finally:
                connection.close()

            print("\nAll timestamp validation tests passed.")

        finally:
            db_connection.DB_PATH = original_db_path


if __name__ == "__main__":
    run_tests()
