
import sqlite3
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = PROJECT_ROOT / "src" / "database" / "schema.sql"


@pytest.fixture
def db():
    """Create a fresh in-memory database for each test."""

    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")

    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    connection.executescript(schema)

    yield connection

    connection.close()


def test_customer_primary_key_uniqueness(db):
    """SQLite should reject duplicate customer IDs."""

    customer = (
        "CUS-000001",
        "Teja",
        "teja@example.com",
        "9876543210",
        0,
        "2026-10-22T00:00:00Z"
    )

    db.execute(
        """
        INSERT INTO customer
        (customer_id, full_name, email, phone, is_vulnerable, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        customer
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO customer
            (customer_id, full_name, email, phone, is_vulnerable, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            customer
        )


def test_foreign_key_rejects_missing_team(db):
    """An agent cannot reference a team that does not exist."""

    db.execute(
        """
        INSERT INTO role (role_id, role_name)
        VALUES ('ROLE-001', 'PROCESS_OWNER')
        """
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO agent
            (agent_id, team_id, role_id, display_name, email)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "AGT-000001",
                "TEAM-999",
                "ROLE-001",
                "Test Agent",
                "agent@example.com"
            )
        )


def test_check_constraint_rejects_negative_price(db):
    """Product prices cannot be negative."""

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO product
            (product_id, product_name, product_category,
             unit_price_paise, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "PRD-000001",
                "Test Product",
                "Electronics",
                -500,
                "2026-10-22T00:00:00Z"
            )
        )


def test_unique_constraint_rejects_duplicate_email(db):
    """Two customers cannot share the same email."""

    customer_1 = (
        "CUS-000001", "Customer One",
        "same@example.com", "9876543210",
        0, "2026-10-22T00:00:00Z"
    )

    customer_2 = (
        "CUS-000002", "Customer Two",
        "same@example.com", "9876543211",
        0, "2026-10-22T00:00:00Z"
    )

    db.execute(
        """
        INSERT INTO customer
        (customer_id, full_name, email, phone, is_vulnerable, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        customer_1
    )

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO customer
            (customer_id, full_name, email, phone, is_vulnerable, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            customer_2
        )
