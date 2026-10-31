def classify_priority(complaint, rules):
    priority_rules = rules["priority"]
    levels = priority_rules["levels"]

    # Map priority ranks to their names.
    priority_by_rank = {
        rank: priority
        for priority, rank in levels.items()
    }

    # Lower rank means higher priority.
    p1_rank = levels["P1"]
    p2_rank = levels["P2"]

    severity = complaint.get("severity")
    sentiment = complaint.get("sentiment")
    if severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise ValueError(f"Unsupported complaint severity: {severity}")

    if sentiment not in {"POSITIVE", "NEUTRAL", "NEGATIVE", None}:
        raise ValueError(f"Unsupported complaint sentiment: {sentiment}")

    is_safety_critical = bool(complaint.get("is_safety_critical", 0))
    is_vulnerable = bool(complaint.get("is_vulnerable", 0))
    is_repeat = bool(complaint.get("is_repeat", 0))

    category_id = complaint.get("category_id")
    order_total_paise = complaint.get("order_total_paise")

    # Rule 1: Safety concerns and critical severity always receive P1.
    if (
        category_id == "CAT-001"
        or is_safety_critical
        or severity == "CRITICAL"
    ):
        return priority_rules["safety_override"]

    # Rule 2: Assign the initial priority from severity.
    severity_priority = {
        "HIGH": "P2",
        "MEDIUM": "P3",
        "LOW": "P4",
    }

    if severity not in severity_priority:
        raise ValueError(f"Unsupported complaint severity: {severity}")

    priority = severity_priority[severity]
    current_rank = levels[priority]

    # Only negative sentiment activates these escalations.
    if sentiment == "NEGATIVE":

        # Rule 3: High-value complaints must be at least P2.
        threshold = priority_rules["high_value_threshold_paise"]

        if (
            order_total_paise is not None
            and int(order_total_paise) >= threshold
        ):
            current_rank = min(current_rank, p2_rank)

        # Rule 4: Vulnerable customers must be at least P2.
        if (
            priority_rules["vulnerable_customer_escalation"]
            and is_vulnerable
        ):
            current_rank = min(current_rank, p2_rank)

        # Rule 5: Repeat negative complaints escalate one level.
        if (
            priority_rules["repeat_complaint_escalation"]
            and is_repeat
        ):
            current_rank = max(p1_rank, current_rank - 1)

    return priority_by_rank[current_rank]