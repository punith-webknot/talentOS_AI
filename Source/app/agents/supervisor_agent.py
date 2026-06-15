from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.postgres import PostgresSaver
from Source.app.config.settings import settings
from Source.app.llms.openai_client import model
from Source.app.prompts.supervisor_agent_prompt import SUPERVISOR_PROMPT

def create_supervisor_agent(job_tool):
    # Using context manager for automatic connection pool management
    with PostgresSaver.from_conn_string(settings.database_uri) as checkpointer:
        # Call setup() only the first time you initialize your database tables
        # checkpointer.setup()
        
        return create_agent(
            model,
            tools=[job_tool], 
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