
import sqlite3
from pathlib import Path


# Project root directory
BASE_DIR = Path(__file__).resolve().parents[2]

# Database location
DB_PATH = BASE_DIR / "output" / "resolveiq.db"


def get_connection():
    """Create and return a SQLite database connection."""

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)

    # Enable foreign-key validation
    connection.execute("PRAGMA foreign_keys = ON")

    return connection
