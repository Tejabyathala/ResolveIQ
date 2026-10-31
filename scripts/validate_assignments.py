import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules

rules = load_business_rules()

routing = {
    key: value
    for key, value in rules["routing"].items()
    if key.startswith("CAT-")
}

errors = []

with get_connection() as connection:

    total_complaints = connection.execute(
        "SELECT COUNT(*) FROM complaint"
    ).fetchone()[0]

    total_assignments = connection.execute("""
        SELECT COUNT(*) FROM assignment WHERE is_current = 1
    """).fetchone()[0]

    missing_assignments = connection.execute("""
        SELECT COUNT(*)
        FROM complaint c
        WHERE NOT EXISTS (
            SELECT 1 FROM assignment a
            WHERE a.complaint_id = c.complaint_id
              AND a.is_current = 1
        )
    """).fetchone()[0]

    wrong_status = connection.execute("""
        SELECT COUNT(*)
        FROM complaint
        WHERE current_status != 'ASSIGNED'
    """).fetchone()[0]

    invalid_agents = connection.execute("""
        SELECT COUNT(*)
        FROM assignment a
        JOIN agent ag ON ag.agent_id = a.agent_id
        JOIN role r ON r.role_id = ag.role_id
        WHERE a.is_current = 1
          AND (
              ag.is_active != 1
              OR r.role_name != 'OPERATIONS_ANALYST'
              OR ag.team_id != a.team_id
          )
    """).fetchone()[0]

    invalid_status_events = connection.execute("""
        SELECT COUNT(*)
        FROM complaint c
        WHERE (
            SELECT COUNT(*)
            FROM complaint_status_event e
            WHERE e.complaint_id = c.complaint_id
              AND e.from_status = 'NEW'
              AND e.to_status = 'ASSIGNED'
        ) != 1
    """).fetchone()[0]

    wrong_team = 0

    assignment_rows = connection.execute("""
        SELECT c.complaint_id, c.category_id, t.team_name
        FROM complaint c
        JOIN assignment a
            ON a.complaint_id = c.complaint_id
           AND a.is_current = 1
        JOIN team t ON t.team_id = a.team_id
    """).fetchall()

    for complaint_id, category_id, actual_team in assignment_rows:
        expected_team = routing.get(category_id)

        if actual_team != expected_team:
            wrong_team += 1
            errors.append(
                f"{complaint_id}: expected {expected_team}, got {actual_team}"
            )

    # Check workload balance within each team.
    workload_rows = connection.execute("""
        SELECT
            t.team_name,
            ag.agent_id,
            COUNT(a.assignment_id) AS workload
        FROM team t
        JOIN agent ag ON ag.team_id = t.team_id
        JOIN role r ON r.role_id = ag.role_id
        LEFT JOIN assignment a
            ON a.agent_id = ag.agent_id
           AND a.is_current = 1
        WHERE ag.is_active = 1
          AND r.role_name = 'OPERATIONS_ANALYST'
        GROUP BY t.team_name, ag.agent_id
        ORDER BY t.team_name, ag.agent_id
    """).fetchall()

    workloads = {}

    for team_name, agent_id, count in workload_rows:
        workloads.setdefault(team_name, []).append(count)

    print("ASSIGNMENT VALIDATION")
    print("=====================")
    print("Total complaints:", total_complaints)
    print("Current assignments:", total_assignments)
    print("Missing assignments:", missing_assignments)
    print("Complaints with wrong status:", wrong_status)
    print("Invalid agents:", invalid_agents)
    print("Incorrect team routing:", wrong_team)
    print("Invalid status-event histories:", invalid_status_events)

    print("\nAGENT WORKLOAD BALANCE")
    print("======================")

    for team, counts in sorted(workloads.items()):
        minimum = min(counts)
        maximum = max(counts)
        print(f"{team}: minimum={minimum}, maximum={maximum}")

        if maximum - minimum > 1:
            errors.append(f"{team}: workload imbalance detected")

    print("\nVALIDATION ERRORS:", len(errors))

    if errors:
        for error in errors[:20]:
            print(error)
    else:
        print("All assignment validations passed.")

if errors or total_complaints != total_assignments or missing_assignments:
    raise SystemExit(1)