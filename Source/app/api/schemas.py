from pydantic import BaseModel, Field

from app.utils.constants import AgentName


class SupervisorResponse(BaseModel):
    messages: list[str] = Field(
        default_factory=list,
        description=(
            "When clarifying an ambiguous request, return one friendly message that "
            "acknowledges the user and asks exactly one question. Never include more "
            "than one question. Leave empty when routing to an agent."
        ),
    )
    next_agent: AgentName
