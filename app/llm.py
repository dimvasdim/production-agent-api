"""
LLM Factory
Returns the chat model for the provider selected in settings,
with automatic fallback to a second model on errors.
"""

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.config import get_settings


def build_model(
    model: str,
    temperature: float = 0,
    timeout: float | None = None,
    max_retries: int | None = None,
) -> BaseChatModel:
    """
    Create a single chat model for the selected provider.
    max_retries defaults to settings.max_retries (only used by Google).
    """
    settings = get_settings()

    if settings.llm_provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            temperature=temperature,
            thinking_level="low",
            timeout=timeout,
            max_retries=settings.max_retries if max_retries is None else max_retries,
        )

    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        reasoning=False,
        client_kwargs={"timeout": timeout} if timeout else {},
    )


def get_llm(temperature: float = 0) -> Runnable:
    """Return the primary model, falling back to the secondary model on failure."""
    settings = get_settings()
    primary = build_model(settings.primary_model, temperature)

    if settings.fallback_model == settings.primary_model:
        return primary

    fallback = build_model(settings.fallback_model, temperature)
    return primary.with_fallbacks([fallback])
