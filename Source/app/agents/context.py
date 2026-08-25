from dataclasses import dataclass


@dataclass
class AgentContext:
    thread_id: str
    user_auth: str | None = None
