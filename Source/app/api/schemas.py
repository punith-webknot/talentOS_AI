from pydantic import BaseModel, Field

from app.utils.constants import AgentName


class SupervisorResponse(BaseModel):
    messages: list[str] = Field(
        default_factory=list,
        description="Maximum 2 follow-up questions if the request is unclear",
    )
    next_agent: AgentName
