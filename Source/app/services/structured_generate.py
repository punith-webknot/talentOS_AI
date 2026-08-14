from typing import Any

from langchain.messages import HumanMessage, SystemMessage

from Source.app.llms.factory import get_evaluation_model, get_model

_DYNAMIC_SCHEMA_TITLE = "StructuredResult"


def _ensure_schema_title(schema: dict[str, Any]) -> dict[str, Any]:
    """Add a top-level title so langchain can bind the raw JSON Schema as a tool."""
    if not schema.get("title"):
        return dict(schema, title=_DYNAMIC_SCHEMA_TITLE)
    return schema


def _build_messages(prompt: str, input_data: dict[str, Any]) -> list:
    system = SystemMessage(
        content=(
            "You are a structured data extraction engine. Follow the provided "
            "instructions and return ONLY valid JSON matching the required schema."
        )
    )
    user_parts = [prompt]
    if input_data:
        user_parts.append("INPUT DATA:\n" + _pretty(input_data))
    user = HumanMessage(content="\n\n".join(user_parts))
    return [system, user]


def _pretty(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, ensure_ascii=False, indent=2)


async def generate_structured(
    prompt: str,
    input_data: dict[str, Any],
    response_schema: dict[str, Any],
    use_evaluation_model: bool = False,
) -> dict[str, Any]:
    """Run a prompt with input data and return JSON matching the given JSON Schema."""
    schema = _ensure_schema_title(response_schema)
    base_model = get_evaluation_model() if use_evaluation_model else get_model()
    structured_model = base_model.with_structured_output(schema, method="function_calling")
    result = await structured_model.ainvoke(_build_messages(prompt, input_data))
    return result if isinstance(result, dict) else dict(result)
