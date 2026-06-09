"""
JD Creation Agent — owns the full job-posting lifecycle end to end.

Adapted to dev's Command/goto + GraphState architecture. The actual work is
delegated to a LangGraph `create_react_agent` (built lazily, once) that pulls
its tools from the talentos-mcp-server over MCP.

--- MCP wiring ---
Tools are NOT local @tool functions. They live behind the talentos-mcp-server
(see /Users/mayurnair/Desktop/talentos_mcp_server), which wraps both
talentos-backend (jobs/drafts/JD/publish) and WebTrak (bands/designations/
bench) behind the Model Context Protocol.

Building the inner react-agent requires an async round-trip (MultiServerMCPClient
spawns the MCP server and performs the MCP `initialize` handshake before tool
schemas are available), so it can't be a module-level singleton built
synchronously at import time. Instead we lazily build-and-cache it on first
use via `get_inner_agent()`, guarded by an asyncio.Lock so concurrent requests
don't race to build it twice.

--- Sync↔async bridge ---
Dev's graph wires this in as a synchronous node (no `async def`). The MCP
react-agent is async, so we run it inside `asyncio.run(...)` from the sync
node. That's safe here because dev currently uses an `InMemorySaver`
checkpointer and synchronous `graph.invoke(...)`. If/when dev moves to an
async runtime, swap the wrapper to `await` directly.
"""
import asyncio
import os
from typing import Literal

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from app.config.settings import settings
from app.prompts.jd_creation import JD_CREATION_PROMPT
from app.state.graph_state import GraphState

_inner_agent = None
_inner_agent_lock = asyncio.Lock()


def _build_mcp_client() -> MultiServerMCPClient:
    """
    Configure the MCP connection to talentos-mcp-server.

    stdio (default, local dev): the agent process spawns
        `uv run python -m talentos_mcp_server.server` as a subprocess and talks
        over stdin/stdout — no extra service to run or port to manage.

    streamable_http (shared/staging): point MCP_SERVER_URL at a
        talentos-mcp-server instance already running with
        MCP_TRANSPORT=streamable-http.
    """
    if settings.MCP_SERVER_TRANSPORT == "streamable_http":
        return MultiServerMCPClient({
            "talentos": {
                "transport": "streamable_http",
                "url": settings.MCP_SERVER_URL,
            }
        })

    return MultiServerMCPClient({
        "talentos": {
            "transport": "stdio",
            "command": "uv",
            "args": [
                "run", "--project", settings.MCP_SERVER_DIR,
                "python", "-m", "talentos_mcp_server.server",
            ],
            "cwd": settings.MCP_SERVER_DIR,
            "env": {
                **os.environ,
                "MCP_TRANSPORT": "stdio",
                # Make sure the spawned MCP server points at the same
                # talentos-backend (and, later, WebTrak) as this app does.
                "TALENTOS_BACKEND_URL": settings.TALENTOS_BACKEND_URL,
                "TALENTOS_BACKEND_TOKEN": settings.TALENTOS_BACKEND_TOKEN,
            },
        }
    })


async def get_inner_agent():
    """
    Lazily build (once) and return the JD react-agent wired to MCP-hosted
    tools. Safe to call concurrently — only the first caller pays the MCP
    handshake cost; everyone else gets the cached agent.
    """
    global _inner_agent
    if _inner_agent is not None:
        return _inner_agent

    async with _inner_agent_lock:
        if _inner_agent is None:
            client = _build_mcp_client()
            tools = await client.get_tools()
            llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                temperature=0.3,
            )
            _inner_agent = create_react_agent(
                model=llm,
                tools=tools,
                prompt=JD_CREATION_PROMPT,
            )
    return _inner_agent


async def _invoke_inner_agent(messages: list[str]) -> str:
    """
    Run the inner MCP react-agent over the conversation so far and return
    its final reply as a string.
    """
    agent = await get_inner_agent()
    # The react-agent expects {"messages": [HumanMessage, AIMessage, ...]} but
    # dev's GraphState carries plain strings. Convert to role-tagged dicts —
    # we assume even-indexed are user turns, odd are assistant turns (matches
    # dev's loop in main.py).
    history = []
    for i, m in enumerate(messages):
        role = "user" if i % 2 == 0 else "assistant"
        history.append({"role": role, "content": m})

    result = await agent.ainvoke({"messages": history})
    last = result["messages"][-1]
    return getattr(last, "content", str(last))


def jd_creation_agent(
    state: GraphState,
) -> Command[Literal["__end__"]]:
    """
    Synchronous LangGraph node. Builds (lazily) and runs the MCP-backed
    react-agent over the current conversation, then appends the reply and
    routes back to END so the supervisor can take the next turn.
    """
    conversation_history = state.get("messages", [])

    reply = asyncio.run(_invoke_inner_agent(conversation_history))

    return Command(
        update={
            "messages": conversation_history + [reply],
        },
        goto=END,
    )
