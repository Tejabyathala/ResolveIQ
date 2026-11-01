
import subprocess
import sys
from pathlib import Path

from src.database.connection import DB_PATH


PROJECT_ROOT = Path(__file__).resolve().parent


def run_step(title, command):
    print(f"\n{'=' * 60}")
    print(title)
    print("=" * 60)

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed: {title}")

    print(f"\n{title} completed successfully.")


def main():
    print("\nRESOLVEIQ - VALIDATION PIPELINE")
    print("=" * 60)

    # Preserve and use the existing development database.
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    print(f"Using existing database: {DB_PATH}")

    # Verify database integrity.
    run_step(
        "DATABASE VERIFICATION",
        [sys.executable, "-m", "src.database.verify_database"],
    )

    # Validate priority decisions.
    run_step(
        "PRIORITY VALIDATION",
        [sys.executable, "scripts/validate_priority_results.py"],
    )

    # Validate team and agent assignments.
    run_step(
        "ASSIGNMENT VALIDATION",
        [sys.executable, "scripts/validate_assignments.py"],
    )

    # Validate SLA clocks and deadlines.
    run_step(
        "SLA VALIDATION",
        [sys.executable, "scripts/validate_sla.py"],
    )

    # Validate complaint messages.
    run_step(
        "MESSAGE VALIDATION",
        [sys.executable, "scripts/validate_messages.py"],
    )

    # Evaluate anomaly detection against ground truth.
    anomaly_db = (
        PROJECT_ROOT
        / "output"
        / "with_anomalies"
        / "resolveiq_anomalies.db"
    )

    ground_truth = (
        PROJECT_ROOT
        / "output"
        / "ground_truth"
        / "ground_truth.csv"
    )

    if not anomaly_db.exists() or not ground_truth.exists():
        raise FileNotFoundError(
            "Anomaly database or ground-truth file is missing."
        )

    run_step(
        "ANOMALY DETECTION EVALUATION",
        [sys.executable, "-m", "src.engine.evaluation"],
    )

    print("\n" + "=" * 60)
    print("RESOLVEIQ PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"\nPIPELINE FAILED: {error}")
        sys.exit(1)
