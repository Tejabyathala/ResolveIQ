from datetime import datetime

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.engine.sla_engine import pause_clock, resume_clock
from contextlib import closing, nullcontext


def validate_event_time(event_at, reference_datetime):
    if event_at > reference_datetime:
        raise ValueError("Event cannot be after the reference datetime.")


def pause_complaint_clocks(
    complaint_id,
    paused_at,
    reason,
    actor_agent_id=None,
    db=None,
):
    rules = load_business_rules()

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    validate_event_time(paused_at, reference_datetime)
    owns_connection = db is None

    connection_context = (
    closing(get_connection())
        if owns_connection
        else nullcontext(db)
    )

    with connection_context as connection:

        clocks = connection.execute("""
            SELECT sla_clock_id, clock_type, deadline_at, clock_status
            FROM sla_clock
            WHERE complaint_id = ?
        """, (complaint_id,)).fetchall()

        if len(clocks) != 2:
            raise ValueError("Expected exactly two SLA clocks.")

        paused_count = 0

        for clock_id, clock_type, deadline_text, status in clocks:

            deadline = datetime.fromisoformat(deadline_text)

            # Do not pause a clock if its deadline has already passed.
            if paused_at >= deadline:
                if status != "BREACHED":
                    connection.execute("""
                        UPDATE sla_clock
                        SET clock_status = 'BREACHED'
                        WHERE sla_clock_id = ?
                    """, (clock_id,))
                continue

            if status not in {"RUNNING", "BREACHED"}:
                raise ValueError(
                    f"Cannot pause {clock_id}: current status is {status}"
                )

            pause_clock("RUNNING", deadline, paused_at)

            event_count = connection.execute("""
                SELECT COUNT(*)
                FROM sla_event
                WHERE sla_clock_id = ?
            """, (clock_id,)).fetchone()[0]

            event_id = f"SLAE-{clock_id}-{event_count + 1:03d}"

            connection.execute("""
                INSERT INTO sla_event (
                    sla_event_id,
                    sla_clock_id,
                    event_type,
                    event_at,
                    reason,
                    actor_agent_id
                )
                VALUES (?, ?, 'PAUSE', ?, ?, ?)
            """, (
                event_id,
                clock_id,
                paused_at.isoformat(),
                reason,
                actor_agent_id,
            ))

            connection.execute("""
                UPDATE sla_clock
                SET clock_status = 'PAUSED'
                WHERE sla_clock_id = ?
            """, (clock_id,))

            paused_count += 1
        if owns_connection:
            connection.commit()
        return paused_count


def resume_complaint_clocks(
    complaint_id,
    resumed_at,
    reason,
    actor_agent_id=None,
    db=None,
):
    rules = load_business_rules()

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    )

    validate_event_time(resumed_at, reference_datetime)

    owns_connection = db is None

    connection_context = (
    closing(get_connection())
    if owns_connection
    else nullcontext(db)
    )

    with connection_context as connection:

        clocks = connection.execute("""
            SELECT
                sla_clock_id,
                clock_status,
                deadline_at,
                total_paused_minutes
            FROM sla_clock
            WHERE complaint_id = ?
              AND clock_status = 'PAUSED'
        """, (complaint_id,)).fetchall()

        if not clocks:
            raise ValueError("No paused SLA clocks found.")

        resumed_count = 0

        for clock_id, status, deadline_text, total_paused in clocks:

            pause_event = connection.execute("""
                SELECT event_at
                FROM sla_event
                WHERE sla_clock_id = ?
                  AND event_type = 'PAUSE'
                ORDER BY event_at DESC, sla_event_id DESC
                LIMIT 1
            """, (clock_id,)).fetchone()

            if pause_event is None:
                raise ValueError(f"No pause history found for {clock_id}.")

            paused_at = datetime.fromisoformat(pause_event[0])
            deadline = datetime.fromisoformat(deadline_text)

            result = resume_clock(
                deadline,
                paused_at,
                resumed_at,
                total_paused,
                reference_datetime,
            )

            event_count = connection.execute("""
                SELECT COUNT(*)
                FROM sla_event
                WHERE sla_clock_id = ?
            """, (clock_id,)).fetchone()[0]

            event_id = f"SLAE-{clock_id}-{event_count + 1:03d}"

            connection.execute("""
                INSERT INTO sla_event (
                    sla_event_id,
                    sla_clock_id,
                    event_type,
                    event_at,
                    reason,
                    actor_agent_id
                )
                VALUES (?, ?, 'RESUME', ?, ?, ?)
            """, (
                event_id,
                clock_id,
                resumed_at.isoformat(),
                reason,
                actor_agent_id,
            ))

            connection.execute("""
                UPDATE sla_clock
                SET deadline_at = ?,
                    total_paused_minutes = ?,
                    clock_status = ?
                WHERE sla_clock_id = ?
            """, (
                result["deadline_at"].isoformat(),
                result["total_paused_minutes"],
                result["clock_status"],
                clock_id,
            ))

            resumed_count += 1
        if owns_connection:
            connection.commit()
        return resumed_count