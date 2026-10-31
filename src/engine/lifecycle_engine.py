ALLOWED_TRANSITIONS = {
    "NEW": {"TRIAGED"},
    "TRIAGED": {"ASSIGNED"},
    "ASSIGNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {
        "PENDING_CUSTOMER",
        "PENDING_APPROVAL",
        "RESOLVED",
    },
    "PENDING_CUSTOMER": {"IN_PROGRESS"},
    "PENDING_APPROVAL": {"IN_PROGRESS", "RESOLVED"},
    "RESOLVED": {"REOPENED", "CLOSED"},
    "REOPENED": {"IN_PROGRESS"},
    "CLOSED": set(),
}


def validate_transition(current_status, new_status):
    if current_status not in ALLOWED_TRANSITIONS:
        raise ValueError(f"Invalid current status: {current_status}")

    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ValueError(
            f"Transition from {current_status} to {new_status} is not allowed."
        )

    return True