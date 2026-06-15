from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from Source.app.agents.context import AgentContext
from Source.app.llms.openai_client import model
from Source.app.prompts.supervisor_agent_prompt import SUPERVISOR_PROMPT


def create_supervisor_agent(job_tool, checkpointer):
    return create_agent(
        model,
        tools=[job_tool],
        context_schema=AgentContext,
        system_prompt=SUPERVISOR_PROMPT,
        middleware=[
            SummarizationMiddleware(
                model=model,
                trigger=("tokens", 50000),
                keep=("messages", 10),
            )
        ],
        checkpointer=checkpointer,
    )


