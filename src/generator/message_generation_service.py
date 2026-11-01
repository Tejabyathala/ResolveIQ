
from contextlib import closing
from datetime import datetime

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.generator.message_generator import generate_messages
from src.engine.message_service import validate_message


def save_messages():
    rules = load_business_rules()

    scale = rules["generation"]["scale"]
    seed = rules["generation"]["seed"]

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace(
            "Z", "+00:00"
        )
    )

    with closing(get_connection()) as connection:
        connection.row_factory = __import__("sqlite3").Row
        complaints = [
            dict(row)
            for row in connection.execute(
                """
                SELECT complaint_id, created_at, channel
                FROM complaint
                ORDER BY complaint_id
                """
            ).fetchall()
        ]

        agents = [
            dict(row)
            for row in connection.execute(
                """
                SELECT agent_id, is_active
                FROM agent
                WHERE is_active = 1
                ORDER BY agent_id
                """
            ).fetchall()
        ]

        if len(complaints) != scale["complaints"]:
            raise ValueError(
                f"Expected {scale['complaints']} complaints, "
                f"found {len(complaints)}."
            )

        messages = generate_messages(
            complaints=complaints,
            agents=agents,
            count=scale["messages"],
            seed=seed,
            reference_datetime=reference_datetime,
        )

        records = []

        for message in messages:
            validate_message(
                sender_type=message["sender_type"],
                sender_agent_id=message["sender_agent_id"],
                channel=message["channel"],
                message_direction=message["message_direction"],
                message_text=message["message_text"],
                sent_at=message["sent_at"],
            )

            records.append((
                message["message_id"],
                message["complaint_id"],
                message["sender_type"],
                message["sender_agent_id"],
                message["channel"],
                message["message_direction"],
                message["message_text"],
                message["sent_at"].isoformat(),
            ))

        with connection:
            connection.executemany(
                """
                INSERT OR IGNORE INTO complaint_message (
                    message_id,
                    complaint_id,
                    sender_type,
                    sender_agent_id,
                    channel,
                    message_direction,
                    message_text,
                    sent_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )

        saved_count = connection.execute(
            "SELECT COUNT(*) FROM complaint_message"
        ).fetchone()[0]

        expected_count = scale["messages"]

        if saved_count != expected_count:
            raise ValueError(
                f"Expected {expected_count} messages in database, "
                f"found {saved_count}."
            )

        print(f"Messages generated: {len(messages)}")
        print(f"Messages in database: {saved_count}")
        print("Message generation completed successfully.")


if __name__ == "__main__":
    save_messages()
