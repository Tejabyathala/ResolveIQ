VALID_RESOLUTION_TYPES = {
    "REFUND",
    "REPLACEMENT",
    "REPAIR",
    "INFORMATION",
    "REJECTED",
}

VALID_RESOLUTION_STATUSES = {
    "PROPOSED",
    "APPROVED",
    "COMPLETED",
    "REJECTED",
}

APPROVER_ROLE_ID = "ROLE-003"


def validate_resolution_request(
    resolution_type,
    refund_amount_paise,
    is_safety_related,
    rules,
):
    if resolution_type not in VALID_RESOLUTION_TYPES:
        raise ValueError("Invalid resolution type.")

    if resolution_type == "REFUND":
        if (
            not isinstance(refund_amount_paise, int)
            or isinstance(refund_amount_paise, bool)
            or refund_amount_paise <= 0
        ):
            raise ValueError("Refund amount must be a positive integer in paise.")
    elif refund_amount_paise is not None:
        raise ValueError(
            "Refund amount is only allowed for REFUND resolutions."
        )

    if resolution_type == "REJECTED":
        raise ValueError(
            "REJECTED is a resolution outcome, not a proposed remedy."
        )

    approval_required = (
        is_safety_related
        and rules["approvals"]["safety_resolution_requires_approval"]
    )

    if resolution_type == "REFUND":
        approval_required = approval_required or (
            refund_amount_paise
            >= rules["approvals"]["refund_threshold_paise"]
        )

    return approval_required


def validate_approver(role_id, is_active):
    if role_id != APPROVER_ROLE_ID:
        raise ValueError("Only APPROVER agents can approve resolutions.")

    if not is_active:
        raise ValueError("Inactive agents cannot approve resolutions.")

    return True


def validate_resolution_transition(
    current_status,
    new_status,
    approval_required,
):
    if current_status not in VALID_RESOLUTION_STATUSES:
        raise ValueError("Invalid current resolution status.")

    if new_status not in VALID_RESOLUTION_STATUSES:
        raise ValueError("Invalid new resolution status.")

    allowed_transitions = {
        "PROPOSED": {"APPROVED", "REJECTED"},
        "APPROVED": {"COMPLETED", "REJECTED"},
        "COMPLETED": set(),
        "REJECTED": set(),
    }

    if (
        current_status == "PROPOSED"
        and new_status == "COMPLETED"
        and not approval_required
    ):
        return True

    if new_status not in allowed_transitions[current_status]:
        raise ValueError(
            f"Invalid resolution transition: "
            f"{current_status} -> {new_status}"
        )

    return True