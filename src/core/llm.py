"""
LLM Configuration for C1 Travel Agent System.
Uses DeepSeek with OpenAI-compatible API.
"""
from functools import lru_cache
from typing import Optional

from langchain_openai import ChatOpenAI
import structlog

from config.settings import settings

logger = structlog.get_logger()


@lru_cache
def get_llm(
    model: str = "deepseek-chat",
    temperature: float = 0.7,
    streaming: bool = True
) -> ChatOpenAI:
    """
    Get configured LLM instance.

    Args:
        model: Model name (default: deepseek-chat)
        temperature: Temperature for generation (default: 0.7)
        streaming: Enable streaming responses (default: True)

    Returns:
        Configured ChatOpenAI instance
    """
    logger.info(
        "Creating LLM instance",
        model=model,
        temperature=temperature,
        base_url=settings.deepseek_base_url
    )

    return ChatOpenAI(
        model=model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=temperature,
        streaming=streaming
    )


def get_structured_llm(
    output_schema,
    model: str = "deepseek-chat",
    temperature: float = 0.0
):
    """
    Get LLM with structured output.

    Args:
        output_schema: Pydantic model or dict schema for output
        model: Model name
        temperature: Temperature (lower for more deterministic)

    Returns:
        LLM with structured output binding
    """
    llm = ChatOpenAI(
        model=model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=temperature,
        streaming=False  # Structured output doesn't support streaming
    )

    return llm.with_structured_output(output_schema)
