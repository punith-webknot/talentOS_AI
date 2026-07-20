import logging

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

from Source.app.llms.factory import get_model
from Source.app.prompts.review_alert_agent_prompt import REVIEW_ALERT_AGENT_PROMPT

logger = logging.getLogger(__name__)


def create_review_alert_agent(mcp_tools: list, checkpointer):
    try:
        model = get_model()
        if not mcp_tools:
            logger.warning(
                "Review/alert agent initialized without MCP tools; "
                "review and alert operations may be unavailable."
            )
        return create_agent(
            model,
            tools=mcp_tools,
            system_prompt=REVIEW_ALERT_AGENT_PROMPT,
            checkpointer=checkpointer,
            middleware=[
                SummarizationMiddleware(
                    model=model,
                    trigger={"tokens": 120000, "messages": 30},
                    keep=("messages", 15),
                ),
            ],
        )
    except Exception:
        logger.exception("Failed to create review/alert agent.")
        raise
