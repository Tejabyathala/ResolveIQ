
import random
from datetime import datetime, timedelta


CUSTOMER_MESSAGES = [
    "I am facing an issue with my recent order.",
    "The product is not working properly.",
    "Please help me resolve this issue.",
    "I am disappointed with the service.",
    "Can you provide an update on my complaint?",
]

AGENT_MESSAGES = [
    "Thank you for contacting support. We are reviewing your issue.",
    "We apologize for the inconvenience caused.",
    "Our team is investigating your complaint.",
    "We will update you shortly.",
    "Thank you for your patience.",
]

SYSTEM_MESSAGES = [
    "Your complaint has been registered successfully.",
    "Your complaint has been assigned to a support agent.",
    "Your complaint status has been updated.",
]


def generate_messages(
    complaints,
    agents,
    count,
    seed,
    reference_datetime,
):
    if count != len(complaints) * 3:
        raise ValueError(
            "Message count must equal three messages per complaint."
        )

    active_agents = [
        agent for agent in agents
        if agent["is_active"]
    ]

    if not active_agents:
        raise ValueError("No active agents available.")

    rng = random.Random(seed + 3)
    messages = []

    for complaint in complaints:
        complaint_id = complaint["complaint_id"]

        created_at = datetime.fromisoformat(
            complaint["created_at"]
        )

        if created_at > reference_datetime:
            raise ValueError(
                "Complaint creation cannot exceed reference datetime."
            )

        available_seconds = int(
            (reference_datetime - created_at).total_seconds()
        )

        offsets = sorted(
            rng.randint(0, available_seconds)
            for _ in range(3)
        )

        selected_agent = rng.choice(active_agents)

        message_data = [
            (
                "CUSTOMER",
                None,
                "INBOUND",
                rng.choice(CUSTOMER_MESSAGES),
            ),
            (
                "SYSTEM",
                None,
                "OUTBOUND",
                rng.choice(SYSTEM_MESSAGES),
            ),
            (
                "AGENT",
                selected_agent["agent_id"],
                "OUTBOUND",
                rng.choice(AGENT_MESSAGES),
            ),
        ]

        for number, data in enumerate(message_data, start=1):
            sender_type, agent_id, direction, message_text = data

            sent_at = created_at + timedelta(
                seconds=offsets[number - 1]
            )

            messages.append({
                "message_id": (
                    f"MSG-{complaint_id}-{number:03d}"
                ),
                "complaint_id": complaint_id,
                "sender_type": sender_type,
                "sender_agent_id": agent_id,
                "channel": complaint["channel"],
                "message_direction": direction,
                "message_text": message_text,
                "sent_at": sent_at,
            })

    return messages
