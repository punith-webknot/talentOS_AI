import logging
from typing import Literal, Optional, TypeVar

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from Source.app.config.settings import Settings, get_settings
from Source.app.llms.gemini_client import create_gemini_model
from Source.app.llms.openai_client import create_openai_model

logger = logging.getLogger(__name__)

_model: Optional[BaseChatModel] = None
_model_provider: Optional[Literal["openai", "gemini"]] = None

T = TypeVar("T", bound=BaseModel)


def get_model() -> BaseChatModel:
    global _model, _model_provider

    settings = get_settings()
    if _model is None or _model_provider != settings.llm_provider:
        _model = _create_model(settings)
        _model_provider = settings.llm_provider

    return _model


def get_structured_model(schema: type[T]) -> object:
    model = get_model()
    settings = get_settings()
    if settings.llm_provider == "gemini":
        return model.with_structured_output(schema, method="json_schema")
    return model.with_structured_output(schema)


def _create_model(settings: Settings) -> BaseChatModel:
    if settings.llm_provider == "openai":
        return create_openai_model(settings)
    if settings.llm_provider == "gemini":
        return create_gemini_model(settings)

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider!r}")
