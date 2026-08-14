import logging

from langchain_openai import ChatOpenAI

from Source.app.config.settings import Settings

logger = logging.getLogger(__name__)


def create_openai_model(settings: Settings, model_name: str | None = None) -> ChatOpenAI:
    resolved_model = model_name or settings.active_model_name
    logger.info(
        "Initializing LLM chat model '%s' via provider '%s' (base_url=%s)",
        resolved_model,
        settings.llm_provider,
        settings.active_base_url,
    )
    return ChatOpenAI(
        model=resolved_model,
        api_key=settings.active_api_key,
        base_url=settings.active_base_url,
    )
