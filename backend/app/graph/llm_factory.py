"""LLM Factory supporting both OpenAI and Google Gemini with hot-swapping."""

import logging
from typing import Any
from langchain_core.language_models.chat_models import BaseChatModel
from app.config import settings

logger = logging.getLogger(__name__)


def get_llm(temperature: float = 0.1) -> BaseChatModel | None:
    """Instantiate and return the configured LLM (OpenAI or Google Gemini)."""
    # 1. Check if OpenAI is enabled and API key is provided
    if settings.use_openai and settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI

            logger.debug(f"Using OpenAI model: {settings.openai_model}")
            return ChatOpenAI(
                model=settings.openai_model,
                api_key=settings.openai_api_key,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatOpenAI: {e}")

    # 2. Otherwise fallback to Google Gemini if configured
    if settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            logger.debug(f"Using Google Gemini model: {settings.gemini_model}")
            return ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                google_api_key=settings.gemini_api_key,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChatGoogleGenerativeAI: {e}")

    return None

