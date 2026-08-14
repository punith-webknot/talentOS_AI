from typing import Optional, TypeVar

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel

from Source.app.config.settings import get_settings
from Source.app.llms.openai_client import create_openai_model

_model: Optional[BaseChatModel] = None
_evaluation_model: Optional[BaseChatModel] = None
_evaluation_model_name: Optional[str] = None

T = TypeVar("T", bound=BaseModel)


def get_model() -> BaseChatModel:
    global _model

    if _model is None:
        _model = create_openai_model(get_settings())

    return _model


def get_evaluation_model() -> BaseChatModel:
    global _evaluation_model, _evaluation_model_name

    settings = get_settings()
    if _evaluation_model is None or _evaluation_model_name != settings.active_evaluation_model_name:
        _evaluation_model = create_openai_model(settings, settings.active_evaluation_model_name)
        _evaluation_model_name = settings.active_evaluation_model_name

    return _evaluation_model


def get_structured_model(schema: type[T]) -> object:
    return get_model().with_structured_output(schema, method="function_calling")


def get_evaluation_structured_model(schema: type[T]) -> object:
    return get_evaluation_model().with_structured_output(schema, method="function_calling")
