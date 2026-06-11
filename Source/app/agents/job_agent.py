from langchain.agents import create_agent
from source.app.llms.openai_client import model
from source.app.prompts.job_agent_prompt import JOB_AGENT_PROMPT

def create_job_agent(mcp_tools: list):
    return create_agent(
        model,
        tools=mcp_tools,
        system_prompt=JOB_AGENT_PROMPT,
    )