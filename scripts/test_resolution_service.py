
import sys
import tempfile

from pathlib import Path
from datetime import datetime, timezone
from contextlib import closing

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import connection as db_connection
from src.engine.resolution_service import propose_resolution


def run_tests():
    original_db_path = db_connection.DB_PATH

    with tempfile.TemporaryDirectory() as temp_dir:
        test_db_path = Path(temp_dir) / "resolution_test.db"
        db_connection.DB_PATH = test_db_path

        try:
            from src.database.initialize import initialize_database

            initialize_database()

            with closing(db_connection.get_connection()) as connection:

                # 1. Insert test customer.
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

                # 2. Insert test product.
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

                # 3. Insert required categories.
                connection.executemany("""
                    INSERT INTO category (
                        category_id, category_name,
                        description, is_active
                    )
                    VALUES (?, ?, ?, ?)
                """, [
                    ("CAT-001", "PRODUCT_SAFETY",
                     "Safety complaints", 1),
                    ("CAT-009", "CUSTOMER_SERVICE",
                     "Customer service complaints", 1),
                ])

                # 4. Insert two complaints.
                complaints = [
                    ("CMP-TEST-001", "CAT-009"),
                    ("CMP-TEST-002", "CAT-001"),
                ]

                for complaint_id, category_id in complaints:
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
                        complaint_id,
                        "CUS-TEST-001",
                        "PRD-TEST-001",
                        category_id,
                        "Test complaint",
                        "Testing resolution service",
                        "EMAIL",
                        "NEGATIVE",
                        "MEDIUM",
                        "P2",
                        0,
                        "IN_PROGRESS",
                        "2026-10-20T00:00:00+00:00",
                    ))

                # 5. Insert two SLA clocks for each complaint.
                sla_clocks = []

                for complaint_id, _ in complaints:
                    sla_clocks.extend([
                        (
                            f"SLA-{complaint_id}-FR",
                            complaint_id,
                            "FIRST_RESPONSE",
                            "2026-10-20T00:00:00+00:00",
                            60,
                            "2026-10-22T00:00:00+00:00",
                            None,
                            "RUNNING",
                            0,
                        ),
                        (
                            f"SLA-{complaint_id}-RS",
                            complaint_id,
                            "RESOLUTION",
                            "2026-10-20T00:00:00+00:00",
                            1440,
                            "2026-10-22T00:00:00+00:00",
                            None,
                            "RUNNING",
                            0,
                        ),
                    ])

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
                """, sla_clocks)

                connection.commit()

            print("Test data inserted successfully.")
            print("Complaints created: 2")
            print("SLA clocks created: 4")

            test_time = datetime(
                2026, 10, 21, 10, 0,
                tzinfo=timezone.utc
            )

            # Test 1: Normal replacement - no approval.
            result1 = propose_resolution(
                "CMP-TEST-001",
                "REPLACEMENT",
                "Replace the defective product.",
                test_time,
            )

            assert result1["approval_required"] is False
            assert result1["resolution_status"] == "PROPOSED"

            # Test 2: Small refund - no approval.
            result2 = propose_resolution(
                "CMP-TEST-001",
                "REFUND",
                "Issue a small refund.",
                test_time,
                refund_amount_paise=500000,
            )

            assert result2["approval_required"] is False

            # Test 3: Refund of ₹10,000 - approval required.
            result3 = propose_resolution(
                "CMP-TEST-001",
                "REFUND",
                "Issue a high-value refund.",
                test_time,
                refund_amount_paise=1000000,
            )

            assert result3["approval_required"] is True

            # Test 4: Safety repair - approval required.
            result4 = propose_resolution(
                "CMP-TEST-002",
                "REPAIR",
                "Repair the safety-related product.",
                test_time,
            )

            assert result4["approval_required"] is True

            # 6. Verify database records and statuses.
            with closing(db_connection.get_connection()) as connection:

                resolution_count = connection.execute(
                    "SELECT COUNT(*) FROM resolution"
                ).fetchone()[0]

                complaint_statuses = connection.execute("""
                    SELECT complaint_id, current_status
                    FROM complaint
                    ORDER BY complaint_id
                """).fetchall()

                paused_clock_count = connection.execute("""
                    SELECT COUNT(*)
                    FROM sla_clock
                    WHERE clock_status = 'PAUSED'
                """).fetchone()[0]

            assert resolution_count == 4
            assert dict(complaint_statuses) == {
                "CMP-TEST-001": "PENDING_APPROVAL",
                "CMP-TEST-002": "PENDING_APPROVAL",
            }
            assert paused_clock_count == 4

            print("\nAll 4 resolution proposal tests passed.")
            print("Resolution records:", resolution_count)
            print("Paused SLA clocks:", paused_clock_count)
            print("Complaint statuses:")

            for complaint_id, status in complaint_statuses:
                print(f"{complaint_id}: {status}")

        finally:
            db_connection.DB_PATH = original_db_path


if __name__ == "__main__":
    run_tests()
