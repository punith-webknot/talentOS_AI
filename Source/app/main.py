from fastapi import FastAPI
from contextlib import asynccontextmanager

from source.app.tools.mcp_client import init_mcp_client
from source.app.tools.agent_tools import get_job_agent_tool, get_interview_agent_tool
from source.app.agents.job_agent import create_job_agent
from source.app.agents.interview_agent import create_interview_agent
from source.app.agents.supervisor_agent import create_supervisor_agent

from source.app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """lifespan allows us to securely attach your heavy objects (the agents and MCP client)
    directly to the app.state.This guarantees that the agents are loaded exactly once into 
    memory when the server starts, and then shared efficiently across all your different API endpoints."""
    
    client, mcp_tools = await init_mcp_client()
    
    job_agent = create_job_agent(mcp_tools)
    interview_agent = create_interview_agent()
    
    job_tool = get_job_agent_tool(job_agent)
    interview_tool = get_interview_agent_tool(interview_agent)
    
    supervisor_agent = create_supervisor_agent(job_tool, interview_tool)
    
    # Store agents globally in the FastAPI app state
    app.state.job_agent = job_agent
    app.state.interview_agent = interview_agent
    app.state.supervisor_agent = supervisor_agent
    
    yield

app = FastAPI(title="TalentOS AI API", lifespan=lifespan)

# Mount the central router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("source.app.main:app", host="127.0.0.1", port=8080, reload=True)