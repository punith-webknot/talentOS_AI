"""MCP tool names assigned to each sub-agent.

Tool implementations live on the remote MCP server. This registry only maps
which fetched tools each agent is allowed to use.
"""

JOB_AGENT_TOOL_NAMES = frozenset(
    {
        "get_benched_candidates",
        "get_all_designations",
        "get_designation_detail",
        "get_all_jobs",
        "get_job_by_id",
        "create_job",
        "update_job",
        "delete_job",
        "list_applications",
        "get_application_by_id",
        "get_users",
        "get_user_by_emp_id",
    }
)

SLOTS_AGENT_TOOL_NAMES = frozenset(
    {
        "ask_form",
        "get_employee_slots",
        "get_employee_form_status",
        "book_interview",
        "get_interviews",
        "get_interview_detail",
    }
)

REVIEW_ALERT_AGENT_TOOL_NAMES = frozenset(
    {
        "get_rounds",
        "get_round_details",
        "get_alerts",
        "read_alert",
        "notify_alert",
    }
)

SUPERVISOR_AGENT_TOOL_NAMES = frozenset(
    {
        "send_mail",
    }
)


def select_tools(mcp_tools: list, tool_names: frozenset[str] | set[str]) -> list:
    """Return MCP tools whose names are in the given allow-list."""
    return [tool for tool in mcp_tools if tool.name in tool_names]
