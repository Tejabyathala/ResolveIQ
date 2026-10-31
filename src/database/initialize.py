
from pathlib import Path

from src.database.connection import get_connection


BASE_DIR = Path(__file__).resolve().parents[2]
SCHEMA_PATH = BASE_DIR / "src" / "database" / "schema.sql"


def initialize_database():
    """Create all database tables from schema.sql."""

    with get_connection() as connection:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")

        connection.executescript(schema)

        print("ResolveIQ database initialized successfully.")


if __name__ == "__main__":
    initialize_database()
