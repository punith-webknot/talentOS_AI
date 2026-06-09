from langgraph.graph import START, StateGraph

from app.agents.interview_scheduler_agent import interview_scheduler_agent
from app.agents.jd_creation_agent import jd_creation_agent
from app.agents.supervisor_agent import supervisor
from app.memory.checkpointer import memory
from app.state.graph_state import GraphState


def build_graph():
    builder = StateGraph(GraphState)

    builder.add_node("supervisor", supervisor)
    builder.add_node("jd_creation_agent", jd_creation_agent)
    builder.add_node("interview_scheduler_agent", interview_scheduler_agent)

    builder.add_edge(START, "supervisor")

    return builder.compile(checkpointer=memory)


graph = build_graph()
