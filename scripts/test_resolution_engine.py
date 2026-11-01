
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.resolution_engine import (
    validate_resolution_request,
    validate_approver,
    validate_resolution_transition,
)

RULES = {
    "approvals": {
        "refund_threshold_paise": 1_000_000,
        "safety_resolution_requires_approval": True,
    }
}

def expect_value_error(function, *args):
    try:
        function(*args)
    except ValueError:
        return
    raise AssertionError("Expected ValueError but no error was raised")
def run_tests():
    # 1. Small refund does not require approval
    assert validate_resolution_request(
        "REFUND", 500_000, False, RULES
    ) is False

    # 2. Refund at threshold requires approval
    assert validate_resolution_request(
        "REFUND", 1_000_000, False, RULES
    ) is True

    # 3. Safety resolution requires approval
    assert validate_resolution_request(
        "REPAIR", None, True, RULES
    ) is True

    # 4. Ordinary replacement does not require approval
    assert validate_resolution_request(
        "REPLACEMENT", None, False, RULES
    ) is False

    # 5. Valid approver
    assert validate_approver("ROLE-003", True) is True

    # 6. Non-approver rejected
    try:
        validate_approver("ROLE-004", True)
        raise AssertionError("Non-approver was accepted")
    except ValueError:
        pass

    # 7. Inactive approver rejected
    try:
        validate_approver("ROLE-003", False)
        raise AssertionError("Inactive approver was accepted")
    except ValueError:
        pass

    # 8. Normal proposed-to-approved transition
    assert validate_resolution_transition(
        "PROPOSED", "APPROVED", True
    ) is True

    # 9. Approved-to-completed transition
    assert validate_resolution_transition(
        "APPROVED", "COMPLETED", True
    ) is True

    # 10. Direct completion without approval
    assert validate_resolution_transition(
        "PROPOSED", "COMPLETED", False
    ) is True

    # 11. Direct completion when approval is required
    try:
        validate_resolution_transition(
            "PROPOSED", "COMPLETED", True
        )
        raise AssertionError("Approval requirement was bypassed")
    except ValueError:
        pass

        # 12. Refund amount cannot be zero
    expect_value_error(
        validate_resolution_request,
        "REFUND", 0, False, RULES
    )

    # 13. Refund amount cannot be negative
    expect_value_error(
        validate_resolution_request,
        "REFUND", -100, False, RULES
    )

    # 14. Refund amount cannot be a decimal
    expect_value_error(
        validate_resolution_request,
        "REFUND", 500.50, False, RULES
    )

    # 15. Refund amount cannot be boolean
    expect_value_error(
        validate_resolution_request,
        "REFUND", True, False, RULES
    )

    # 16. Non-refund resolution cannot have refund amount
    expect_value_error(
        validate_resolution_request,
        "REPLACEMENT", 50000, False, RULES
    )

    # 17. Invalid resolution type
    expect_value_error(
        validate_resolution_request,
        "CASHBACK", None, False, RULES
    )

    # 18. Invalid transition
    expect_value_error(
        validate_resolution_transition,
        "COMPLETED", "PROPOSED", False
    )

    print("All 18 resolution engine tests passed.")
    


if __name__ == "__main__":
    run_tests()