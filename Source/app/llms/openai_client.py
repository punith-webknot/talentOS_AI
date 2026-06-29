import logging

from langchain_openai import ChatOpenAI

from Source.app.config.settings import Settings

logger = logging.getLogger(__name__)


def create_openai_model(settings: Settings) -> ChatOpenAI:
    logger.info("Initializing OpenAI chat model '%s'", settings.model_name)
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
    )
