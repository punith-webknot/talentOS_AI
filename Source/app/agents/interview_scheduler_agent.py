from typing import Literal

from langgraph.graph import END
from langgraph.types import Command

from app.state.graph_state import GraphState


def interview_scheduler_agent(
    state: GraphState,
) -> Command[Literal["__end__"]]:
    conversation_history = state.get("messages", [])

    return Command(
        update={
            "messages": conversation_history + [
                "Interview Scheduler Agent Invoked punith",
            ],
        },
        goto=END,
    )
