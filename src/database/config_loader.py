
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "business_rules.yaml"


def load_business_rules():
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Business rules file not found: {CONFIG_PATH}"
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        rules = yaml.safe_load(file)

    if not isinstance(rules, dict):
        raise ValueError("Business rules must contain a YAML dictionary.")

    required_sections = [
        "project",
        "generation",
        "priority",
        "sla",
        "repeat_complaints",
        "approvals",
        "routing",
        "statuses",
    ]

    missing_sections = [
        section
        for section in required_sections
        if section not in rules
    ]

    if missing_sections:
        raise ValueError(
            f"Missing configuration sections: {missing_sections}"
        )

    required_generation = [
        "seed",
        "reference_datetime",
        "currency",
        "scale",
    ]

    missing_generation = [
        key
        for key in required_generation
        if key not in rules["generation"]
    ]

    if missing_generation:
        raise ValueError(
            f"Missing generation settings: {missing_generation}"
        )

    if not isinstance(rules["generation"]["scale"], dict):
        raise ValueError("generation.scale must be a dictionary.")

    return rules


if __name__ == "__main__":
    business_rules = load_business_rules()

    print("Business rules loaded successfully!")
    print("Project:", business_rules["project"]["name"])
    print("Seed:", business_rules["generation"]["seed"])
    print(
        "Scale settings:",
        business_rules["generation"]["scale"]
    )
    print("Available sections:", list(business_rules.keys()))
