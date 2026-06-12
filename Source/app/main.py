from contextlib import asynccontextmanager

from fastapi import FastAPI

from Source.app.agents.job_agent import create_job_agent
from Source.app.agents.supervisor_agent import create_supervisor_agent
from Source.app.api.router import api_router
from Source.app.tools.agent_tools import get_job_agent_tool
from Source.app.tools.mcp_client import init_mcp_client

@asynccontextmanager
async def lifespan(app: FastAPI):
    """lifespan allows us to securely attach your heavy objects (the agents and MCP client)
    directly to the app.state.This guarantees that the agents are loaded exactly once into 
    memory when the server starts, and then shared efficiently across all your different API endpoints."""
    
    _, mcp_tools = await init_mcp_client()
    
    job_agent = create_job_agent(mcp_tools)
    job_tool = get_job_agent_tool(job_agent)
    supervisor_agent = create_supervisor_agent(job_tool)
    
    # Store agents globally in the FastAPI app state
    app.state.job_agent = job_agent
    app.state.supervisor_agent = supervisor_agent
    
    yield

app = FastAPI(title="TalentOS AI API", lifespan=lifespan)

# Mount the central router
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("Source.app.main:app", host="127.0.0.1", port=8080, reload=True)
