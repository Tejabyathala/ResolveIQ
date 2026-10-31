import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.sla_engine import (
    pause_clock,
    calculate_paused_minutes,
    resume_clock,
)

start = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)


def test_pause_running_clock():
    deadline = start + timedelta(hours=4)

    assert pause_clock("RUNNING", deadline, start) == "PAUSED"


def test_cannot_pause_breached_clock():
    deadline = start + timedelta(hours=1)

    try:
        pause_clock("BREACHED", deadline, start)
    except ValueError:
        return

    raise AssertionError("Expected ValueError")


def test_pause_after_deadline():
    deadline = start + timedelta(hours=1)
    pause_time = start + timedelta(hours=2)

    try:
        pause_clock("RUNNING", deadline, pause_time)
    except ValueError:
        return

    raise AssertionError("Expected ValueError")


def test_pause_duration():
    paused_at = start
    resumed_at = start + timedelta(minutes=30)

    assert calculate_paused_minutes(paused_at, resumed_at) == 30


def test_partial_minute_rounds_up():
    paused_at = start
    resumed_at = start + timedelta(seconds=30)

    assert calculate_paused_minutes(paused_at, resumed_at) == 1


def test_deadline_extension():
    deadline = start + timedelta(hours=4)
    paused_at = start + timedelta(hours=1)
    resumed_at = paused_at + timedelta(minutes=30)

    result = resume_clock(
        deadline,
        paused_at,
        resumed_at,
        0,
        start + timedelta(hours=2),
    )

    assert result["deadline_at"] == deadline + timedelta(minutes=30)
    assert result["total_paused_minutes"] == 30
    assert result["clock_status"] == "RUNNING"


def test_resumed_clock_can_still_be_breached():
    deadline = start + timedelta(hours=1)
    paused_at = start + timedelta(minutes=30)
    resumed_at = paused_at + timedelta(minutes=30)

    result = resume_clock(
        deadline,
        paused_at,
        resumed_at,
        0,
        start + timedelta(hours=3),
    )

    assert result["clock_status"] == "BREACHED"


if __name__ == "__main__":
    tests = [
        test_pause_running_clock,
        test_cannot_pause_breached_clock,
        test_pause_after_deadline,
        test_pause_duration,
        test_partial_minute_rounds_up,
        test_deadline_extension,
        test_resumed_clock_can_still_be_breached,
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