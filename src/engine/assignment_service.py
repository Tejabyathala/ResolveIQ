from collections import Counter
from datetime import datetime

from src.database.connection import get_connection
from src.database.config_loader import load_business_rules
from src.engine.assignment_engine import select_agent


ACTIVE_STATUSES = (
    "ASSIGNED",
    "IN_PROGRESS",
    "PENDING_CUSTOMER",
    "PENDING_APPROVAL",
)


def assign_complaints():
    rules = load_business_rules()

    reference_datetime = datetime.fromisoformat(
        rules["generation"]["reference_datetime"].replace("Z", "+00:00")
    ).isoformat()

    routing = {
        key: value
        for key, value in rules["routing"].items()
        if key.startswith("CAT-")
    }

    if rules["routing"]["assignment_strategy"] != "lowest_active_workload":
        raise ValueError("Unsupported assignment strategy.")

    if rules["routing"]["tie_breaker"] != "agent_id_ascending":
        raise ValueError("Unsupported tie-breaker.")

    priority_levels = rules["priority"]["levels"]

    with get_connection() as connection:

        # Map team names to database IDs.
        teams = {
            row[1]: row[0]
            for row in connection.execute("""
                SELECT team_id, team_name
                FROM team
                WHERE is_active = 1
            """).fetchall()
        }

        # Load only active operational analysts.
        agent_rows = connection.execute("""
            SELECT a.agent_id, a.team_id
            FROM agent a
            JOIN role r ON r.role_id = a.role_id
            WHERE a.is_active = 1
              AND r.role_name = 'OPERATIONS_ANALYST'
            ORDER BY a.agent_id
        """).fetchall()

        agents_by_team = {}

        for agent_id, team_id in agent_rows:
            agents_by_team.setdefault(team_id, []).append({
                "agent_id": agent_id,
            })

        # Calculate existing active workload.
        placeholders = ",".join("?" for _ in ACTIVE_STATUSES)

        workload_rows = connection.execute(f"""
            SELECT a.agent_id, COUNT(*)
            FROM assignment a
            JOIN complaint c ON c.complaint_id = a.complaint_id
            WHERE a.is_current = 1
              AND c.current_status IN ({placeholders})
              AND a.agent_id IS NOT NULL
            GROUP BY a.agent_id
        """, ACTIVE_STATUSES).fetchall()

        workload = {
            agent["agent_id"]: 0
            for agents in agents_by_team.values()
            for agent in agents
        }

        for agent_id, count in workload_rows:
            if agent_id in workload:
                workload[agent_id] = count

        # Find complaints that are NEW and have no current assignment.
        complaints = connection.execute("""
            SELECT
                c.complaint_id,
                c.category_id,
                c.priority
            FROM complaint c
            WHERE c.current_status = 'NEW'
              AND c.priority IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM assignment a
                  WHERE a.complaint_id = c.complaint_id
                    AND a.is_current = 1
              )
            ORDER BY
                CASE c.priority
                    WHEN 'P1' THEN 1
                    WHEN 'P2' THEN 2
                    WHEN 'P3' THEN 3
                    WHEN 'P4' THEN 4
                END,
                c.created_at,
                c.complaint_id
        """).fetchall()

        assignment_records = []
        status_events = []
        complaint_updates = []

        team_counts = Counter()
        agent_counts = Counter()

        for number, (complaint_id, category_id, priority) in enumerate(
            complaints, start=1
        ):

            team_name = routing.get(category_id)

            if not team_name or team_name not in teams:
                raise ValueError(
                    f"No valid team mapping for category {category_id}"
                )

            team_id = teams[team_name]
            eligible_agents = agents_by_team.get(team_id, [])

            if not eligible_agents:
                raise ValueError(
                    f"No active operational analysts in {team_name}"
                )

            selected_agent = select_agent(
                eligible_agents,
                workload,
            )

            agent_id = selected_agent["agent_id"]

            # Increase workload immediately for subsequent assignments.
            workload[agent_id] += 1

            team_counts[team_name] += 1
            agent_counts[agent_id] += 1

            assignment_records.append((
                f"ASN-{number:06d}",
                complaint_id,
                team_id,
                agent_id,
                reference_datetime,
                None,
                None,
                "Category routing; lowest active workload; "
                "agent_id ascending tie-breaker",
                1,
            ))

            status_events.append((
                f"CSE-{number:06d}",
                complaint_id,
                "NEW",
                "ASSIGNED",
                reference_datetime,
                None,
                "Automatically assigned by ResolveIQ",
            ))

            complaint_updates.append((complaint_id,))

        # Save all changes in one transaction.
        connection.executemany("""
            INSERT INTO assignment (
                assignment_id,
                complaint_id,
                team_id,
                agent_id,
                assigned_at,
                unassigned_at,
                assigned_by_agent_id,
                assignment_reason,
                is_current
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, assignment_records)

        connection.executemany("""
            INSERT INTO complaint_status_event (
                status_event_id,
                complaint_id,
                from_status,
                to_status,
                changed_at,
                actor_agent_id,
                reason
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, status_events)

        connection.executemany("""
            UPDATE complaint
            SET current_status = 'ASSIGNED'
            WHERE complaint_id = ?
        """, complaint_updates)

        # Verify assignment totals before committing.
        assigned_count = connection.execute("""
            SELECT COUNT(*)
            FROM assignment
            WHERE is_current = 1
        """).fetchone()[0]

        if assigned_count != sum(
            1 for _ in connection.execute("""
                SELECT complaint_id
                FROM assignment
                WHERE is_current = 1
            """)
        ):
            raise ValueError("Assignment verification failed.")

    print("\nCOMPLAINT ASSIGNMENT SUMMARY")
    print("============================")
    print("New complaints assigned:", len(complaints))
    print("Teams receiving assignments:", len(team_counts))
    print("Agents receiving assignments:", len(agent_counts))

    print("\nTEAM DISTRIBUTION")
    for team, count in sorted(team_counts.items()):
        print(f"{team}: {count}")

    print("\nTotal assignments created:", len(assignment_records))
    print("Status events created:", len(status_events))


if __name__ == "__main__":
    assign_complaints()