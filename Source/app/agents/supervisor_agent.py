from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END
from langgraph.types import Command

from app.llms.openai_client import get_supervisor_llm
from app.prompts.supervisor import SUPERVISOR_PROMPT
from app.state.graph_state import GraphState
from dotenv import load_dotenv

load_dotenv()

llm = get_supervisor_llm()


def supervisor(
    state: GraphState,
) -> Command[
    Literal[
        "jd_creation_agent",
        "interview_scheduler_agent",
        "__end__",
    ]
]:
    prompt = ChatPromptTemplate.from_template(SUPERVISOR_PROMPT)
    chain = prompt | llm

    conversation_history = state.get("messages", [])

    response = chain.invoke(
        {
            "conversation": "\n".join(conversation_history),
        }
    )

    if response.next_agent == "jd_creation_agent":
        return Command(
            update={
                "next_agent": "jd_creation_agent",
            },
            goto="jd_creation_agent",
        )

    if response.next_agent == "interview_scheduler_agent":
        return Command(
            update={
                "next_agent": "interview_scheduler_agent",
            },
            goto="interview_scheduler_agent",
        )

    return Command(
        update={
            "messages": conversation_history + response.messages,
            "next_agent": "END",
        },
        goto=END,
    )
