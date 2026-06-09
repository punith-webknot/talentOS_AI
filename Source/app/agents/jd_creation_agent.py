from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from app.state.graph_state import GraphState


def jd_creation_agent(
    state: GraphState,
) -> Command[Literal["__end__"]]:
    conversation_history = state.get("messages", [])

    return Command(
        update={
            "messages": conversation_history + [
                "JD Creation Agent Invoked",
            ],
        },
        goto=END,
    )