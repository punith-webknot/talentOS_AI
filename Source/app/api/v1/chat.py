import json
from typing import Any, AsyncGenerator
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain.messages import AIMessageChunk
from langchain_core.runnables import RunnableConfig


from Source.app.agents.context import AgentContext
from Source.app.api.dependencies import get_supervisor_agent

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "1"


def _preprocess_command_execution(message: str) -> str:
    try:
        parsed = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        return message

    if not isinstance(parsed, dict) or parsed.get("message_type") != "COMMAND_EXECUTION":
        return message

    intent = parsed.get("intent")
    payload: dict[str, Any] = parsed.get("payload", {})
    raw_text = payload.pop("raw_text_context", "")

    if intent == "book-interview":
        for key in list(payload.keys()):
            if key.endswith(("_name", "_title", "_label")):
                del payload[key]
        parts = ["Please book an interview with the following details:"]
        for key, value in payload.items():
            parts.append(f"  - {key}: {json.dumps(value)}")
        if raw_text:
            parts.append(f"\nAdditional context from user: {raw_text}")
        parts.append("\nAll required fields are provided above. Call book_interview with these values.")
        return "\n".join(parts)

    if intent == "interviews":
        interview_id = payload.get("interview_id", "")
        parts = [f"The user is asking about interview {interview_id}."]
        if raw_text:
            parts.append(f"\nUser's question: {raw_text}")
        parts.append("\nUse get_interview_detail to look up the interview and answer the user's question.")
        return "\n".join(parts)

    if intent == "rounds":
        round_id = payload.get("round_id", "")
        candidate_id = payload.get("candidate_id", "")
        parts = [f"The user is asking about round {round_id}."]
        if candidate_id:
            parts.append(f"\nThe candidate id is {candidate_id}.")
        if raw_text:
            parts.append(f"\nUser's question: {raw_text}")
        parts.append("\nUse get_round_details to look up the round and answer the user's question.")
        return "\n".join(parts)

    if intent == "alerts":
        for key in list(payload.keys()):
            if key.endswith(("_name", "_title", "_label")):
                del payload[key]
        alert_id = payload.get("alert_id", "")
        alert_type = payload.get("alert_type", "")
        employee_id = payload.get("employee_id") or payload.get("userId") or ""
        parts = [f"The user is asking about alert {alert_id} (type: {alert_type})."]
        if employee_id:
            parts.append(f"The employee user ID for this alert is {employee_id}.")
        if raw_text:
            parts.append(f"\nUser's question: {raw_text}")
        parts.append("\nUse notify_alert with the employee user_id to send the notification.")
        return "\n".join(parts)

    if intent == "SEND_MAIL":
        for key in list(payload.keys()):
            if key.endswith(("_name", "_title", "_label")):
                del payload[key]
        employee_name = payload.get("employee_name", "")
        employee_email = payload.get("employee_email", "")
        parts = [f"The user wants to send an email to {employee_name}."]
        if employee_email:
            parts.append(f"The recipient's email address is {employee_email}.")
        if raw_text:
            parts.append(f"\nUser's message: {raw_text}")
        parts.append("\nUse send_mail to send the email.")
        return "\n".join(parts)

    return message


UI_EDITABLE_START = "[[UI:EDITABLE]]"
UI_EDITABLE_END = "[[/UI:EDITABLE]]"


def _partial_marker_suffix(text: str, marker: str) -> int:
    """Return length of a trailing prefix of `marker` present at the end of `text`."""
    max_check = min(len(text), len(marker) - 1)
    for size in range(max_check, 0, -1):
        if marker.startswith(text[-size:]):
            return size
    return 0


class _EditableUiStreamParser:
    """Split streamed text so only content between UI markers is marked EDITABLE."""

    def __init__(self) -> None:
        self._inside = False
        self._buf = ""

    def reset(self) -> None:
        self._inside = False
        self._buf = ""

    def feed(self, text: str) -> list[tuple[str, bool]]:
        self._buf += text
        segments: list[tuple[str, bool]] = []

        while self._buf:
            marker = UI_EDITABLE_END if self._inside else UI_EDITABLE_START
            idx = self._buf.find(marker)
            if idx == -1:
                keep = _partial_marker_suffix(self._buf, marker)
                emit = self._buf[:-keep] if keep else self._buf
                self._buf = self._buf[-keep:] if keep else ""
                if emit:
                    segments.append((emit, self._inside))
                break

            before = self._buf[:idx]
            if before:
                segments.append((before, self._inside))
            self._buf = self._buf[idx + len(marker) :]
            if self._buf.startswith("\n"):
                self._buf = self._buf[1:]
            self._inside = not self._inside

        return segments

    def flush(self) -> list[tuple[str, bool]]:
        if not self._buf:
            return []
        leftover = self._buf
        self._buf = ""
        return [(leftover, self._inside)]


async def event_generator(user_query: str, thread_id: str, supervisor_agent) -> AsyncGenerator[str, None]:
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    context = AgentContext(thread_id=thread_id)
    resolved_query = _preprocess_command_execution(user_query)
    ui_parser = _EditableUiStreamParser()

    async for chunk in supervisor_agent.astream(
        {"messages": [{"role": "user", "content": resolved_query}]},
        config=config,
        context=context,
        stream_mode=["messages"],
        version="v2"
    ):
        if chunk["type"] == "messages":
            token, metadata = chunk["data"]
            if isinstance(token, AIMessageChunk):
                if token.tool_call_chunks:
                    ui_parser.reset()
                    for tc in token.tool_call_chunks:
                        if tc.get("name") is not None:
                            yield json.dumps({"type": "stream", "steps": [{"type": "tool_name", "content": tc["name"]}], "final": []}) + "\n"
                        if tc.get("args") is not None and tc["args"] != "":
                            yield json.dumps({"type": "stream", "steps": [{"type": "tool_args", "content": tc["args"]}], "final": []}) + "\n"
                elif token.text:
                    for content, editable in ui_parser.feed(token.text):
                        if not content:
                            continue
                        final_item: dict[str, Any] = {"type": "markdown", "content": content}
                        if editable:
                            final_item["ui"] = "EDITABLE"
                        yield json.dumps({"type": "stream", "steps": [], "final": [final_item]}) + "\n"

    for content, editable in ui_parser.flush():
        if not content:
            continue
        final_item: dict[str, Any] = {"type": "markdown", "content": content}
        if editable:
            final_item["ui"] = "EDITABLE"
        yield json.dumps({"type": "stream", "steps": [], "final": [final_item]}) + "\n"


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