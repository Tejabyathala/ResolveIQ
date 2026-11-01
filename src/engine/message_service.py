
from datetime import datetime, timezone

from src.database.connection import get_connection
from contextlib import closing

VALID_SENDER_TYPES = {"CUSTOMER", "AGENT", "SYSTEM"}

VALID_CHANNELS = {
    "EMAIL",
    "PHONE",
    "WEB",
    "CHAT",
    "SOCIAL",
}

VALID_DIRECTIONS = {"INBOUND", "OUTBOUND"}


def validate_message(
    sender_type,
    sender_agent_id,
    channel,
    message_direction,
    message_text,
    sent_at,
):
    if sender_type not in VALID_SENDER_TYPES:
        raise ValueError("Invalid sender type.")

    if channel not in VALID_CHANNELS:
        raise ValueError("Invalid message channel.")

    if message_direction not in VALID_DIRECTIONS:
        raise ValueError("Invalid message direction.")

    if sender_type == "AGENT" and not sender_agent_id:
        raise ValueError("Agent messages require an agent ID.")

    if sender_type in {"CUSTOMER", "SYSTEM"} and sender_agent_id is not None:
        raise ValueError(
            "Customer and system messages cannot have an agent ID."
        )

    if not isinstance(message_text, str) or not message_text.strip():
        raise ValueError("Message text cannot be empty.")

    if not isinstance(sent_at, datetime):
        raise ValueError("sent_at must be a datetime.")

    if sent_at.tzinfo is None or sent_at.utcoffset() is None:
        raise ValueError("Message timestamp must be timezone-aware.")

    return True

def record_complaint_message(
    complaint_id,
    sender_type,
    sender_agent_id,
    channel,
    message_direction,
    message_text,
    sent_at,
):
    validate_message(
        sender_type,
        sender_agent_id,
        channel,
        message_direction,
        message_text,
        sent_at,
    )

    from src.database.config_loader import load_business_rules

    rules = load_business_rules()
    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    if sent_at > reference_datetime:
        raise ValueError("Message cannot be after the reference datetime.")

    with closing(get_connection()) as connection:
        with connection:
            complaint = connection.execute(
                """
                SELECT complaint_id, created_at
                FROM complaint
                WHERE complaint_id = ?
                """,
                (complaint_id,),
            ).fetchone()

            if complaint is None:
                raise ValueError("Complaint does not exist.")

            complaint_created_at = datetime.fromisoformat(
                complaint[1].replace("Z", "+00:00")
            )
            latest_message = connection.execute(
                """
                SELECT sent_at
                FROM complaint_message
                WHERE complaint_id = ?
                ORDER BY sent_at DESC
                LIMIT 1
                """,
                (complaint_id,),
            ).fetchone()

            if latest_message:
                latest_message_at = datetime.fromisoformat(
                    latest_message[0]
                )

                if sent_at < latest_message_at:
                    raise ValueError(
                        "Message cannot be before the previous message."
                    )

            if sent_at < complaint_created_at:
                raise ValueError(
                    "Message cannot be before complaint creation."
                )

            if sender_type == "AGENT":
                agent = connection.execute(
                    """
                    SELECT agent_id, is_active
                    FROM agent
                    WHERE agent_id = ?
                    """,
                    (sender_agent_id,),
                ).fetchone()

                if agent is None or not agent[1]:
                    raise ValueError("Agent does not exist or is inactive.")

            previous_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM complaint_message
                WHERE complaint_id = ?
                """,
                (complaint_id,),
            ).fetchone()[0]

            message_id = (
                f"MSG-{complaint_id}-{previous_count + 1:03d}"
            )

            connection.execute(
                """
                INSERT INTO complaint_message (
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
                (
                    message_id,
                    complaint_id,
                    sender_type,
                    sender_agent_id,
                    channel,
                    message_direction,
                    message_text.strip(),
                    sent_at.isoformat(),
                ),
            )

            return message_id
