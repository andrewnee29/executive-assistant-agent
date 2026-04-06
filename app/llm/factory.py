from app.config import Settings
from app.llm.base import LLMProvider


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Instantiate the correct LLM provider based on LLM_PROVIDER in .env."""
    provider = settings.llm_provider.lower()

    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=settings.anthropic_api_key,
            model=settings.llm_model,
        )

    if provider == "openai":
        from app.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
        )

    raise ValueError(
        f"Unknown LLM provider '{provider}'. "
        "Set LLM_PROVIDER to 'anthropic' or 'openai' in .env."
    )
