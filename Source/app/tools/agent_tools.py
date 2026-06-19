from langchain.tools import tool, ToolRuntime

from Source.app.agents.context import AgentContext


def get_job_agent_tool(job_agent_instance):
    """Factory to create the job agent tool with an injected agent instance."""

    @tool
    async def job_agent_tool(request: str, runtime: ToolRuntime[AgentContext]) -> str:
        """Delegate to the JD Management Agent for job descriptions and job postings."""
        human_messages = [m for m in runtime.state["messages"] if m.type == "human"]
        latest_user_message = human_messages[-1].content if human_messages else request
        prompt = (
            f"User's latest message:\n{latest_user_message}\n\n"
            f"Delegated task:\n{request}"
        )

        result = await job_agent_instance.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"configurable": {"thread_id": f"{runtime.context.thread_id}-job"}},
        )
        return result["messages"][-1].content

    return job_agent_tool
