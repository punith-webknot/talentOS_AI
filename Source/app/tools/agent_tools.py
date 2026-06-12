from langchain.tools import tool, ToolRuntime

def get_job_agent_tool(job_agent_instance):
    """Factory to create the job agent tool with an injected agent instance."""
    
    @tool
    async def job_agent_tool(request: str, runtime: ToolRuntime) -> str:
        """Use this tool to draft or refine job descriptions and job postings."""
        original_user_message = next(
            message for message in runtime.state["messages"]
            if message.type == "human"
        )

        prompt = (
            "You are assisting with the following user inquiry:\n\n"
            f"{original_user_message.content}\n\n"
            "You are tasked with the following sub-request:\n\n"
            f"{request}"
        )

        result = await job_agent_instance.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]}
        )
        return result["messages"][-1].content
        
    return job_agent_tool