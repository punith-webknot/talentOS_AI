from typing_extensions import TypedDict

from app.utils.constants import AgentName


class GraphState(TypedDict):
    messages: list[str]
    next_agent: AgentName
