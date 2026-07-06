import logging

from langchain_openai import ChatOpenAI

from Source.app.config.settings import Settings

logger = logging.getLogger(__name__)


def create_openai_model(settings: Settings, model_name: str | None = None) -> ChatOpenAI:
    resolved_model = model_name or settings.model_name
    logger.info("Initializing OpenAI chat model '%s'", resolved_model)
    return ChatOpenAI(
        model=resolved_model,
        api_key=settings.openai_api_key,
    )
