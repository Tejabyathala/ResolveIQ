from datetime import datetime, timedelta
import math

def calculate_deadline(started_at, target_minutes):
    """
    Calculate an SLA deadline using elapsed 24/7 time.
    """

    if target_minutes <= 0:
        raise ValueError("SLA target must be greater than zero.")

    return started_at + timedelta(minutes=target_minutes)


def determine_clock_status(deadline_at, reference_datetime):
    """
    Determine whether an SLA is currently running or breached.
    """

    if reference_datetime >= deadline_at:
        return "BREACHED"

    return "RUNNING"


def get_sla_targets(priority, rules):
    """
    Retrieve first-response and resolution targets from YAML.
    """

    targets = rules["sla"]["targets"]

    if priority not in targets:
        raise ValueError(f"Invalid complaint priority: {priority}")

    return targets[priority]



def pause_clock(clock_status, deadline_at, paused_at):
    """
    Pause an SLA clock only if it has not already breached.
    """

    if clock_status != "RUNNING":
        raise ValueError("Only a running SLA clock can be paused.")

    if paused_at >= deadline_at:
        raise ValueError("Cannot pause an SLA clock after its deadline.")

    return "PAUSED"


def calculate_paused_minutes(paused_at, resumed_at):
    """
    Calculate pause duration, rounding up to whole minutes.
    """

    if resumed_at <= paused_at:
        raise ValueError("Resume time must be after pause time.")

    seconds = (resumed_at - paused_at).total_seconds()

    return math.ceil(seconds / 60)


def resume_clock(
    deadline_at,
    paused_at,
    resumed_at,
    total_paused_minutes,
    reference_datetime,
):
    """
    Extend the deadline by the paused duration and determine status.
    """

    if total_paused_minutes < 0:
        raise ValueError("Total paused minutes cannot be negative.")

    paused_minutes = calculate_paused_minutes(
        paused_at,
        resumed_at,
    )

    updated_deadline = deadline_at + timedelta(
        minutes=paused_minutes
    )

    updated_total = total_paused_minutes + paused_minutes

    updated_status = determine_clock_status(
        updated_deadline,
        reference_datetime,
    )

    return {
        "deadline_at": updated_deadline,
        "total_paused_minutes": updated_total,
        "clock_status": updated_status,
    }