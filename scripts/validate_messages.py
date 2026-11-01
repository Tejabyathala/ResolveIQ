import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection


def validate_messages():
    connection = get_connection()
    connection.row_factory = __import__("sqlite3").Row

    errors = []

    total = connection.execute(
        "SELECT COUNT(*) FROM complaint_message"
    ).fetchone()[0]

    incorrect_distribution = connection.execute(
        """
        SELECT complaint_id, COUNT(*) AS message_count
        FROM complaint_message
        GROUP BY complaint_id
        HAVING COUNT(*) != 3
        """
    ).fetchall()

    invalid_agents = connection.execute(
        """
        SELECT m.message_id
        FROM complaint_message m
        LEFT JOIN agent a ON m.sender_agent_id = a.agent_id
        WHERE m.sender_type = 'AGENT'
          AND (a.agent_id IS NULL OR a.is_active != 1)
        """
    ).fetchall()

    missing_messages = connection.execute(
        """
        SELECT c.complaint_id
        FROM complaint c
        LEFT JOIN complaint_message m
          ON c.complaint_id = m.complaint_id
        GROUP BY c.complaint_id
        HAVING COUNT(m.message_id) = 0
        """
    ).fetchall()

    foreign_key_errors = connection.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    if total != 6000:
        errors.append(f"Expected 6000 messages, found {total}")

    if incorrect_distribution:
        errors.append(
            f"{len(incorrect_distribution)} complaints "
            "do not have exactly 3 messages"
        )

    if invalid_agents:
        errors.append(
            f"{len(invalid_agents)} messages have invalid agents"
        )

    if missing_messages:
        errors.append(
            f"{len(missing_messages)} complaints have no messages"
        )

    if foreign_key_errors:
        errors.append("Foreign key violations found")

    print("TOTAL MESSAGES:", total)
    print("INCORRECT DISTRIBUTION:", len(incorrect_distribution))
    print("INVALID AGENTS:", len(invalid_agents))
    print("COMPLAINTS WITHOUT MESSAGES:", len(missing_messages))
    print("FOREIGN KEY ERRORS:", len(foreign_key_errors))

    connection.close()

    if errors:
        for error in errors:
            print("ERROR:", error)
        raise SystemExit(1)

    print("\nAll message validation checks passed.")


if __name__ == "__main__":
    validate_messages()
