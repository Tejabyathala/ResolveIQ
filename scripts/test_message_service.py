
import sys
import tempfile

from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import connection as db_connection
from src.engine.message_service import record_complaint_message


def run_tests():
    original_db_path = db_connection.DB_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        db_connection.DB_PATH = Path(temp_dir) / "message_test.db"

        try:
            from src.database.initialize import initialize_database

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
                    "test@example.com",
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
                    "Testing message service",
                    "EMAIL",
                    "NEGATIVE",
                    "MEDIUM",
                    "P2",
                    0,
                    "IN_PROGRESS",
                    "2026-10-20T00:00:00+00:00",
                ))

                connection.execute("""
                    INSERT INTO team (
                        team_id, team_name, description, is_active
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    "TEAM-TEST-001",
                    "Test Team",
                    "Message service testing",
                    1,
                ))

                connection.execute("""
                    INSERT INTO role (
                        role_id, role_name, description
                    )
                    VALUES (?, ?, ?)
                """, (
                    "ROLE-TEST-001",
                    "OPERATIONS_ANALYST",
                    "Test role",
                ))

                connection.execute("""
                    INSERT INTO agent (
                        agent_id, team_id, role_id,
                        display_name, email, is_active,
                        capacity_weight
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    "AGT-TEST-001",
                    "TEAM-TEST-001",
                    "ROLE-TEST-001",
                    "Test Agent",
                    "agent@example.com",
                    1,
                    1,
                ))

                connection.commit()

            test_time = datetime(
                2026, 10, 21, 10, 0,
                tzinfo=timezone.utc,
            )

            # Test 1: Customer inbound message.
            customer_message = record_complaint_message(
                "CMP-TEST-001",
                "CUSTOMER",
                None,
                "EMAIL",
                "INBOUND",
                "I received a damaged product.",
                test_time,
            )

            assert customer_message == "MSG-CMP-TEST-001-001"

            # Test 2: Agent outbound message.
            agent_message = record_complaint_message(
                "CMP-TEST-001",
                "AGENT",
                "AGT-TEST-001",
                "EMAIL",
                "OUTBOUND",
                "We are investigating your complaint.",
                test_time,
            )

            assert agent_message == "MSG-CMP-TEST-001-002"

            # Test 3: System outbound message.
            system_message = record_complaint_message(
                "CMP-TEST-001",
                "SYSTEM",
                None,
                "WEB",
                "OUTBOUND",
                "Your complaint has been registered.",
                test_time,
            )

            assert system_message == "MSG-CMP-TEST-001-003"

            # Test 4: Invalid sender type.
            try:
                record_complaint_message(
                    "CMP-TEST-001",
                    "INVALID",
                    None,
                    "EMAIL",
                    "INBOUND",
                    "Invalid sender.",
                    test_time,
                )
                raise AssertionError("Invalid sender was accepted.")
            except ValueError:
                pass

            # Test 5: Agent without agent ID.
            try:
                record_complaint_message(
                    "CMP-TEST-001",
                    "AGENT",
                    None,
                    "EMAIL",
                    "OUTBOUND",
                    "Missing agent.",
                    test_time,
                )
                raise AssertionError("Missing agent ID was accepted.")
            except ValueError:
                pass

            # Test 6: Invalid channel.
            try:
                record_complaint_message(
                    "CMP-TEST-001",
                    "CUSTOMER",
                    None,
                    "INVALID",
                    "INBOUND",
                    "Invalid channel.",
                    test_time,
                )
                raise AssertionError("Invalid channel was accepted.")
            except ValueError:
                pass

            # Test 7: Empty message.
            try:
                record_complaint_message(
                    "CMP-TEST-001",
                    "CUSTOMER",
                    None,
                    "EMAIL",
                    "INBOUND",
                    "   ",
                    test_time,
                )
                raise AssertionError("Empty message was accepted.")
            except ValueError:
                pass

            # Test 8: Nonexistent complaint.
            try:
                record_complaint_message(
                    "CMP-MISSING",
                    "CUSTOMER",
                    None,
                    "EMAIL",
                    "INBOUND",
                    "Unknown complaint.",
                    test_time,
                )
                raise AssertionError("Unknown complaint was accepted.")
            except ValueError:
                pass

                        # Test 9: Message before complaint creation.
            try:
                record_complaint_message(
                    "CMP-TEST-001",
                    "CUSTOMER",
                    None,
                    "EMAIL",
                    "INBOUND",
                    "Old message.",
                    datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc),
                )
                raise AssertionError("Earlier message was accepted.")
            except ValueError:
                pass

            # Test 10: Message before previous message.
            try:
                record_complaint_message(
                    "CMP-TEST-001",
                    "CUSTOMER",
                    None,
                    "EMAIL",
                    "INBOUND",
                    "Out-of-order message.",
                    datetime(2026, 10, 21, 9, 0, tzinfo=timezone.utc),
                )
                raise AssertionError("Out-of-order message was accepted.")
            except ValueError:
                pass

            print("Timestamp boundary tests passed.")
            # Verify saved records.
            with closing(db_connection.get_connection()) as connection:
                records = connection.execute("""
                    SELECT message_id, sender_type, sender_agent_id
                    FROM complaint_message
                    ORDER BY message_id
                """).fetchall()

            assert len(records) == 3
            assert records[0][1] == "CUSTOMER"
            assert records[0][2] is None
            assert records[1][1] == "AGENT"
            assert records[1][2] == "AGT-TEST-001"
            assert records[2][1] == "SYSTEM"
            assert records[2][2] is None

            print("Customer message test passed.")
            print("Agent message test passed.")
            print("System message test passed.")
            print("Invalid input tests passed.")
            print("Database verification passed.")
            print("\nAll 10 message service tests passed.")

        finally:
            db_connection.DB_PATH = original_db_path


if __name__ == "__main__":
    run_tests()
