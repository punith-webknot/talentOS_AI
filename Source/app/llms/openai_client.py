from langchain_openai import ChatOpenAI

from app.api.schemas import SupervisorResponse

def get_supervisor_llm():
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    ).with_structured_output(SupervisorResponse)
