import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.lifecycle_engine import validate_transition

# Valid transitions
valid_cases = [
    ("NEW", "TRIAGED"),
    ("TRIAGED", "ASSIGNED"),
    ("ASSIGNED", "IN_PROGRESS"),
    ("IN_PROGRESS", "PENDING_CUSTOMER"),
    ("PENDING_CUSTOMER", "IN_PROGRESS"),
    ("IN_PROGRESS", "RESOLVED"),
    ("RESOLVED", "REOPENED"),
    ("REOPENED", "IN_PROGRESS"),
    ("RESOLVED", "CLOSED"),
]

# Invalid transitions
invalid_cases = [
    ("NEW", "RESOLVED"),
    ("ASSIGNED", "CLOSED"),
    ("CLOSED", "IN_PROGRESS"),
    ("IN_PROGRESS", "NEW"),
]

for current, new in valid_cases:
    assert validate_transition(current, new) is True

for current, new in invalid_cases:
    try:
        validate_transition(current, new)
        raise AssertionError(
            f"Invalid transition was accepted: {current} -> {new}"
        )
    except ValueError:
        pass

print(f"Valid transitions passed: {len(valid_cases)}")
print(f"Invalid transitions rejected: {len(invalid_cases)}")
print("All lifecycle engine tests passed.")