from datetime import datetime
from contextlib import closing,nullcontext

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.engine.lifecycle_engine import validate_transition
from src.engine.sla_event_service import (
    pause_complaint_clocks,
    resume_complaint_clocks,
)


PENDING_STATUSES = {
    "PENDING_CUSTOMER",
    "PENDING_APPROVAL",
}

def validate_transition_time(connection, complaint_id, changed_at):
    if not isinstance(changed_at, datetime):
        raise ValueError("changed_at must be a datetime object.")

    if changed_at.tzinfo is None or changed_at.utcoffset() is None:
        raise ValueError("changed_at must include timezone information.")

    rules = load_business_rules()

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    if changed_at > reference_datetime:
        raise ValueError(
            "Transition cannot be after the reference datetime."
        )

    complaint = connection.execute("""
        SELECT created_at
        FROM complaint
        WHERE complaint_id = ?
    """, (complaint_id,)).fetchone()

    if complaint is None:
        raise ValueError(f"Complaint {complaint_id} does not exist.")

    created_at = datetime.fromisoformat(complaint[0])

    if changed_at < created_at:
        raise ValueError(
            "Transition cannot be before complaint creation."
        )

    latest_event = connection.execute("""
        SELECT MAX(changed_at)
        FROM complaint_status_event
        WHERE complaint_id = ?
    """, (complaint_id,)).fetchone()[0]

    if latest_event:
        latest_event_at = datetime.fromisoformat(latest_event)

        if changed_at <= latest_event_at:
            raise ValueError(
                "Transition must occur after the latest status event."
            )

def transition_complaint(
    complaint_id,
    new_status,
    changed_at,
    reason,
    actor_agent_id=None,
    db=None,
):
    owns_connection = db is None

    connection_context = (
        closing(get_connection())
        if owns_connection
        else nullcontext(db)
    )

    with connection_context as connection:
        transaction_context = (
            connection
            if owns_connection
            else nullcontext(connection)
        )

        with transaction_context:

            complaint = connection.execute("""
                SELECT current_status
                FROM complaint
                WHERE complaint_id = ?
            """, (complaint_id,)).fetchone()

            if complaint is None:
                raise ValueError(
                    f"Complaint not found: {complaint_id}"
                )

            current_status = complaint[0]

            validate_transition(current_status, new_status)

            validate_transition_time(
                connection,
                complaint_id,
                changed_at,
            )

            entering_pending = (
                new_status in PENDING_STATUSES
                and current_status not in PENDING_STATUSES
            )

            leaving_pending = (
                current_status in PENDING_STATUSES
                and new_status not in PENDING_STATUSES
            )

            if entering_pending:
                pause_complaint_clocks(
                    complaint_id,
                    changed_at,
                    reason,
                    actor_agent_id,
                    db=connection,
                )

            elif leaving_pending:
                resume_complaint_clocks(
                    complaint_id,
                    changed_at,
                    reason,
                    actor_agent_id,
                    db=connection,
                )

            event_count = connection.execute("""
                SELECT COUNT(*)
                FROM complaint_status_event
            """).fetchone()[0]

            status_event_id = f"STSE-{event_count + 1:07d}"

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
                status_event_id,
                complaint_id,
                current_status,
                new_status,
                changed_at.isoformat(),
                actor_agent_id,
                reason,
            ))

            connection.execute("""
                UPDATE complaint
                SET current_status = ?
                WHERE complaint_id = ?
            """, (new_status, complaint_id))

            result = {
                "complaint_id": complaint_id,
                "previous_status": current_status,
                "current_status": new_status,
                "status_event_id": status_event_id,
            }

            if owns_connection:
                connection.commit()

            return result