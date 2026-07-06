import logging

from langchain.messages import AIMessageChunk

logger = logging.getLogger(__name__)


def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        logger.debug("%s|", token.text)
    if token.tool_call_chunks:
        logger.debug("Tool call chunks: %s", token.tool_call_chunks)