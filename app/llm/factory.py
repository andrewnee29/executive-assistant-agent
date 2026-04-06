import os

from app.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    """Return the configured LLMProvider instance.

    Reads LLM_PROVIDER from the environment (default: "anthropic").
    Raises ValueError for unsupported providers or missing API keys.
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    if provider == "anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or environment."
            )
        from app.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key)

    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file or environment."
            )
        model = os.environ.get("LLM_MODEL", "gpt-4o")
        from app.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, model=model)

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{provider}'. "
        "Valid options: 'anthropic', 'openai'."
    )
