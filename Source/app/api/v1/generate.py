from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from Source.app.services.structured_generate import generate_structured

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    input_data: dict[str, Any] = Field(default_factory=dict)
    response_schema: dict[str, Any]
    use_evaluation_model: bool = False


class GenerateResponse(BaseModel):
    result: dict[str, Any]


@router.post("/generate", response_model=GenerateResponse)
async def generate_endpoint(payload: GenerateRequest) -> GenerateResponse:
    """Run a generic prompt + input data and return JSON matching the caller's JSON Schema."""
    result = await generate_structured(
        prompt=payload.prompt,
        input_data=payload.input_data,
        response_schema=payload.response_schema,
        use_evaluation_model=payload.use_evaluation_model,
    )
    return GenerateResponse(result=result)
