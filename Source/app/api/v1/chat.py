import json
from typing import AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.runnables import RunnableConfig
from langchain.messages import AIMessageChunk


from Source.app.agents.context import AgentContext
from Source.app.api.dependencies import get_supervisor_agent

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "1"

async def event_generator(user_query: str, thread_id: str, supervisor_agent) -> AsyncGenerator[str, None]:
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    context = AgentContext(thread_id=thread_id)

    async for chunk in supervisor_agent.astream(
        {"messages": [{"role": "user", "content": user_query}]},
        config=config,
        context=context,
        stream_mode=["messages"],
        version="v2"
    ):
        if chunk["type"] == "messages":
            token, metadata = chunk["data"]
            if isinstance(token, AIMessageChunk):
                if token.tool_call_chunks:
                    for tc in token.tool_call_chunks:
                        if tc.get("name") is not None:
                            yield json.dumps({"type": "stream", "steps": [{"type": "tool_name", "content": tc["name"]}], "final": []}) + "\n"
                        if tc.get("args") is not None and tc["args"] != "":
                            yield json.dumps({"type": "stream", "steps": [{"type": "tool_args", "content": tc["args"]}], "final": []}) + "\n"
                elif token.text:
                    yield json.dumps({"type": "stream", "steps": [], "final": [{"type": "markdown", "content": token.text}]}) + "\n"

@router.post("/stream")
async def stream_chat_endpoint(
    payload: ChatRequest,
    supervisor_agent=Depends(get_supervisor_agent),
):
    """Exposes real-time agent generation streaming."""
    return StreamingResponse(
        event_generator(payload.message, payload.thread_id, supervisor_agent),
        media_type="application/x-ndjson"
    )