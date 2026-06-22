import logging
from typing import Optional

from langchain_openai import ChatOpenAI

from Source.app.config.settings import get_settings

logger = logging.getLogger(__name__)
_model: Optional[ChatOpenAI] = None


def get_model() -> ChatOpenAI:
    global _model
    if _model is None:
        settings = get_settings()
        logger.info("Initializing OpenAI chat model '%s'", settings.model_name)
        _model = ChatOpenAI(
            model=settings.model_name,
            api_key=settings.openai_api_key,
        )
    return _model