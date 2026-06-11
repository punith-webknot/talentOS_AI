from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from source.app.llms.openai_client import model
from source.app.prompts.supervisor_agent_prompt import SUPERVISOR_PROMPT

def create_supervisor_agent(job_tool, interview_tool):
    checkpointer = InMemorySaver()
    
    return create_agent(
        model,
        tools=[job_tool, interview_tool], 
        system_prompt=SUPERVISOR_PROMPT,
        middleware=[
            SummarizationMiddleware(
                model="gpt-4.1-mini",
                trigger=("tokens", 50000),
                keep=("messages", 10),
            )
        ],
        checkpointer=checkpointer,
    )