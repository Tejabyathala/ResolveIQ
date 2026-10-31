def select_agent(agents, workload):
    """
    Select the agent with the lowest active workload.
    Break ties using ascending agent_id.
    """
    if not agents:
        raise ValueError("No eligible agents available.")

    return min(
        agents,
        key=lambda agent: (
            workload[agent["agent_id"]],
            agent["agent_id"],
        ),
    )