from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Executive Assistant Agent"
    debug: bool = False
    secret_key: str
    user_name: str = "the user"

    # LLM Provider ("anthropic" or "openai")
    llm_provider: str = "anthropic"
    llm_model: str = "claude-opus-4-6"

    # Anthropic
    anthropic_api_key: str = ""

    # OpenAI
    openai_api_key: str = ""

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Database
    database_url: str = "sqlite:///./data/app.db"

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
