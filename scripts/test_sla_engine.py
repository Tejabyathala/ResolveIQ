import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.sla_engine import (
    calculate_deadline,
    determine_clock_status,
    get_sla_targets,
)
from src.database.config_loader import load_business_rules


def test_deadline_calculation():
    start = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    deadline = calculate_deadline(start, 60)

    assert deadline == start + timedelta(hours=1)


def test_p1_resolution_deadline():
    start = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    deadline = calculate_deadline(start, 240)

    assert deadline == start + timedelta(hours=4)


def test_running_status():
    deadline = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)
    reference = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    assert determine_clock_status(deadline, reference) == "RUNNING"


def test_breached_status():
    deadline = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)
    reference = datetime(2026, 10, 22, 12, 0, tzinfo=timezone.utc)

    assert determine_clock_status(deadline, reference) == "BREACHED"


def test_exact_deadline_is_breached():
    deadline = datetime(2026, 10, 22, 11, 0, tzinfo=timezone.utc)

    assert determine_clock_status(deadline, deadline) == "BREACHED"


def test_invalid_target():
    start = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    try:
        calculate_deadline(start, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for zero target.")


def test_yaml_sla_targets():
    rules = load_business_rules()

    assert get_sla_targets("P1", rules) == {
        "first_response_minutes": 15,
        "resolution_minutes": 240,
    }

    assert get_sla_targets("P4", rules) == {
        "first_response_minutes": 480,
        "resolution_minutes": 4320,
    }


if __name__ == "__main__":
    tests = [
        test_deadline_calculation,
        test_p1_resolution_deadline,
        test_running_status,
        test_breached_status,
        test_exact_deadline_is_breached,
        test_invalid_target,
        test_yaml_sla_targets,
    ]

    passed = 0

    for test in tests:
        try:
            test()
            print(f"PASS: {test.__name__}")
            passed += 1
        except Exception as error:
            print(f"FAIL: {test.__name__}: {error}")

    print(f"\nResults: {passed}/{len(tests)} tests passed.")

    if passed != len(tests):
        raise SystemExit(1)