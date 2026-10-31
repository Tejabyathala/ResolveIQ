import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.config_loader import load_business_rules
from src.engine.priority_engine import classify_priority

rules = load_business_rules()

test_cases = [
    (
        "Product safety",
        {"category_id": "CAT-001", "severity": "LOW"},
        "P1",
    ),
    (
        "Critical severity",
        {"severity": "CRITICAL"},
        "P1",
    ),
    (
        "High severity",
        {"severity": "HIGH"},
        "P2",
    ),
    (
        "Medium severity",
        {"severity": "MEDIUM"},
        "P3",
    ),
    (
        "Low severity",
        {"severity": "LOW"},
        "P4",
    ),
    (
        "Vulnerable customer with negative sentiment",
        {
            "severity": "MEDIUM",
            "sentiment": "NEGATIVE",
            "is_vulnerable": 1,
        },
        "P2",
    ),
    (
        "High-value negative complaint",
        {
            "severity": "LOW",
            "sentiment": "NEGATIVE",
            "order_total_paise": 6000000,
        },
        "P2",
    ),
    (
        "Repeat negative complaint",
        {
            "severity": "MEDIUM",
            "sentiment": "NEGATIVE",
            "is_repeat": 1,
        },
        "P2",
    ),
    (
        "Positive repeat complaint",
        {
            "severity": "MEDIUM",
            "sentiment": "POSITIVE",
            "is_repeat": 1,
        },
        "P3",
    ),
]

passed = 0

for name, complaint, expected in test_cases:
    actual = classify_priority(complaint, rules)

    if actual == expected:
        print(f"PASS: {name} -> {actual}")
        passed += 1
    else:
        print(
            f"FAIL: {name} | Expected: {expected}, Actual: {actual}"
        )

print(f"\nResults: {passed}/{len(test_cases)} tests passed")

if passed != len(test_cases):
    raise SystemExit(1)