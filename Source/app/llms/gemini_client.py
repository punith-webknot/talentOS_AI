import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from Source.app.config.settings import Settings

logger = logging.getLogger(__name__)


def create_gemini_model(settings: Settings) -> ChatGoogleGenerativeAI:
    logger.info("Initializing Gemini chat model '%s'", settings.model_name)
    return ChatGoogleGenerativeAI(
        model=settings.model_name,
        api_key=settings.google_api_key,
    )
