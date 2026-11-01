from contextlib import closing
from datetime import datetime, timezone

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules

from src.engine.resolution_engine import (
    validate_resolution_request,
    validate_approver,
    validate_resolution_transition,
)

from src.engine.lifecycle_service import transition_complaint
from src.engine.sla_event_service import stop_complaint_clocks

def propose_resolution(
    complaint_id,
    resolution_type,
    resolution_notes,
    created_at,
    refund_amount_paise=None,
):
    rules = load_business_rules()

    with closing(get_connection()) as connection:
        with connection:

            complaint = connection.execute("""
                SELECT
                    c.current_status,
                    c.category_id,
                    c.product_id
                FROM complaint c
                WHERE c.complaint_id = ?
            """, (complaint_id,)).fetchone()

            if complaint is None:
                raise ValueError(
                    f"Complaint not found: {complaint_id}"
                )

            current_status, category_id, product_id = complaint

            if current_status != "IN_PROGRESS":
                raise ValueError(
                    "Resolution can only be proposed for "
                    "IN_PROGRESS complaints."
                )

            if not isinstance(resolution_notes, str) or not resolution_notes.strip():
                raise ValueError("Resolution notes cannot be empty.")

            # Identify safety-related complaints.
            is_safety_related = category_id == "CAT-001"

            if product_id is not None:
                product = connection.execute("""
                    SELECT is_safety_critical
                    FROM product
                    WHERE product_id = ?
                """, (product_id,)).fetchone()

                if product and product[0]:
                    is_safety_related = True

            # Validate resolution request and approval requirement.
            approval_required = validate_resolution_request(
                resolution_type,
                refund_amount_paise,
                is_safety_related,
                rules,
            )

            # Generate a resolution ID.
            resolution_count = connection.execute("""
                SELECT COUNT(*)
                FROM resolution
            """).fetchone()[0]

            resolution_id = f"RES-{complaint_id}-{resolution_count + 1:03d}"

            # Create resolution record.
            connection.execute("""
                INSERT INTO resolution (
                    resolution_id,
                    complaint_id,
                    resolution_type,
                    resolution_notes,
                    resolved_at,
                    approved_by_agent_id,
                    resolution_status,
                    refund_amount_paise,
                    created_at
                )
                VALUES (?, ?, ?, ?, NULL, NULL, 'PROPOSED', ?, ?)
            """, (
                resolution_id,
                complaint_id,
                resolution_type,
                resolution_notes.strip(),
                refund_amount_paise,
                created_at.isoformat(),
            ))

            # Pause complaint SLA clocks if approval is required.
            if approval_required:
                transition_complaint(
                    complaint_id,
                    "PENDING_APPROVAL",
                    created_at,
                    "Resolution requires approval.",
                    db=connection,
                )

            return {
                "resolution_id": resolution_id,
                "complaint_id": complaint_id,
                "resolution_type": resolution_type,
                "resolution_status": "PROPOSED",
                "approval_required": approval_required,
            }

def approve_resolution(
    resolution_id,
    approver_agent_id,
    approved_at,
):
    with closing(get_connection()) as connection:
        with connection:

            # 1. Find the resolution and its complaint.
            resolution = connection.execute("""
                SELECT
                    r.complaint_id,
                    r.resolution_status,
                    c.current_status
                FROM resolution r
                JOIN complaint c
                    ON c.complaint_id = r.complaint_id
                WHERE r.resolution_id = ?
            """, (resolution_id,)).fetchone()

            if resolution is None:
                raise ValueError(
                    f"Resolution not found: {resolution_id}"
                )

            complaint_id, resolution_status, complaint_status = resolution

            # 2. Ensure the resolution is awaiting approval.
            if resolution_status != "PROPOSED":
                raise ValueError(
                    "Only proposed resolutions can be approved."
                )

            if complaint_status != "PENDING_APPROVAL":
                raise ValueError(
                    "Complaint is not awaiting approval."
                )

            # 3. Verify the approving agent.
            agent = connection.execute("""
                SELECT role_id, is_active
                FROM agent
                WHERE agent_id = ?
            """, (approver_agent_id,)).fetchone()

            if agent is None:
                raise ValueError(
                    f"Approver agent not found: {approver_agent_id}"
                )

            role_id, is_active = agent

            validate_approver(role_id, is_active)

            # 4. Validate the resolution transition.
            validate_resolution_transition(
                resolution_status,
                "APPROVED",
                approval_required=True,
            )

            # 5. Record approval.
            connection.execute("""
                UPDATE resolution
                SET
                    approved_by_agent_id = ?,
                    resolution_status = 'APPROVED'
                WHERE resolution_id = ?
            """, (
                approver_agent_id,
                resolution_id,
            ))

            # 6. Resume complaint lifecycle and SLA clocks.
            transition_complaint(
                complaint_id,
                "IN_PROGRESS",
                approved_at,
                "Resolution approved.",
                actor_agent_id=approver_agent_id,
                db=connection,
            )

            return {
                "resolution_id": resolution_id,
                "complaint_id": complaint_id,
                "resolution_status": "APPROVED",
                "approved_by_agent_id": approver_agent_id,
                "complaint_status": "IN_PROGRESS",
            }

def reject_resolution(
    resolution_id,
    approver_agent_id,
    rejected_at,
    reason,
):
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("Rejection reason cannot be empty.")

    with closing(get_connection()) as connection:
        with connection:

            # Find the resolution and complaint.
            resolution = connection.execute("""
                SELECT
                    r.complaint_id,
                    r.resolution_status,
                    c.current_status
                FROM resolution r
                JOIN complaint c
                    ON c.complaint_id = r.complaint_id
                WHERE r.resolution_id = ?
            """, (resolution_id,)).fetchone()

            if resolution is None:
                raise ValueError(
                    f"Resolution not found: {resolution_id}"
                )

            complaint_id, resolution_status, complaint_status = resolution

            if resolution_status != "PROPOSED":
                raise ValueError(
                    "Only proposed resolutions can be rejected."
                )

            if complaint_status != "PENDING_APPROVAL":
                raise ValueError(
                    "Complaint is not awaiting approval."
                )

            # Verify the approver.
            agent = connection.execute("""
                SELECT role_id, is_active
                FROM agent
                WHERE agent_id = ?
            """, (approver_agent_id,)).fetchone()

            if agent is None:
                raise ValueError(
                    f"Approver agent not found: {approver_agent_id}"
                )

            validate_approver(agent[0], agent[1])

            # Validate resolution transition.
            validate_resolution_transition(
                resolution_status,
                "REJECTED",
                approval_required=True,
            )

            # Reject the resolution.
            connection.execute("""
                UPDATE resolution
                SET resolution_status = 'REJECTED'
                WHERE resolution_id = ?
            """, (resolution_id,))

            # Return complaint to IN_PROGRESS and resume SLA clocks.
            transition_complaint(
                complaint_id,
                "IN_PROGRESS",
                rejected_at,
                f"Resolution rejected: {reason.strip()}",
                actor_agent_id=approver_agent_id,
                db=connection,
            )

            return {
                "resolution_id": resolution_id,
                "complaint_id": complaint_id,
                "resolution_status": "REJECTED",
                "complaint_status": "IN_PROGRESS",
                "rejected_by_agent_id": approver_agent_id,
            }

def complete_resolution(
    resolution_id,
    resolved_at,
    actor_agent_id=None,
):
    rules = load_business_rules()

    with closing(get_connection()) as connection:
        with connection:

            # 1. Retrieve resolution and complaint details.
            resolution = connection.execute("""
                SELECT
                    r.complaint_id,
                    r.resolution_type,
                    r.refund_amount_paise,
                    r.resolution_status,
                    c.current_status,
                    c.category_id,
                    c.product_id
                FROM resolution r
                JOIN complaint c
                    ON c.complaint_id = r.complaint_id
                WHERE r.resolution_id = ?
            """, (resolution_id,)).fetchone()

            if resolution is None:
                raise ValueError(
                    f"Resolution not found: {resolution_id}"
                )

            (
                complaint_id,
                resolution_type,
                refund_amount,
                resolution_status,
                complaint_status,
                category_id,
                product_id,
            ) = resolution

            # 2. Complaint must be in progress.
            if complaint_status != "IN_PROGRESS":
                raise ValueError(
                    "Complaint must be IN_PROGRESS to complete resolution."
                )

            # 3. Identify safety-related complaints.
            is_safety_related = category_id == "CAT-001"

            if product_id is not None:
                product = connection.execute("""
                    SELECT is_safety_critical
                    FROM product
                    WHERE product_id = ?
                """, (product_id,)).fetchone()

                if product and product[0]:
                    is_safety_related = True

            # 4. Recalculate whether approval was required.
            approval_required = validate_resolution_request(
                resolution_type,
                refund_amount,
                is_safety_related,
                rules,
            )

            # 5. Validate the resolution transition.
            validate_resolution_transition(
                resolution_status,
                "COMPLETED",
                approval_required,
            )

            # 6. Move complaint to RESOLVED.
            transition_complaint(
                complaint_id,
                "RESOLVED",
                resolved_at,
                "Resolution completed.",
                actor_agent_id=actor_agent_id,
                db=connection,
            )

            # 7. Stop both SLA clocks.
            stop_complaint_clocks(
                complaint_id,
                resolved_at,
                "Complaint resolution completed.",
                actor_agent_id=actor_agent_id,
                db=connection,
            )

            # 8. Update resolution record.
            connection.execute("""
                UPDATE resolution
                SET
                    resolution_status = 'COMPLETED',
                    resolved_at = ?
                WHERE resolution_id = ?
            """, (
                resolved_at.isoformat(),
                resolution_id,
            ))

            return {
                "resolution_id": resolution_id,
                "complaint_id": complaint_id,
                "resolution_status": "COMPLETED",
                "complaint_status": "RESOLVED",
                "resolved_at": resolved_at.isoformat(),
                "sla_clocks_stopped": 2,
            }
