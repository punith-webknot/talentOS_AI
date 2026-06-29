import logging

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

from Source.app.agents.context import AgentContext
from Source.app.llms.factory import get_model
from Source.app.prompts.supervisor_agent_prompt import SUPERVISOR_PROMPT

logger = logging.getLogger(__name__)


def create_supervisor_agent(job_tool, checkpointer):
    try:
        model = get_model()
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
    except Exception:
        logger.exception("Failed to create supervisor agent.")
        raise


