"""
Centralized Configuration
Uses pydantic-settings for validated environment variables.
"""

from typing import Literal

from dotenv import load_dotenv
from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache

# Load .env into os.environ so LangChain/LangSmith SDK can read tracing config
load_dotenv()

# (primary, fallback) used when PRIMARY_MODEL / FALLBACK_MODEL are not set
DEFAULT_MODELS = {
    "google": ("gemini-3.6-flash", "gemini-3.5-flash-lite"),
    "ollama": ("qwen3.5:4b", "qwen2.5:7b"),
}

class Settings(BaseSettings):

    # LLM Configuration
    llm_provider: Literal["google", "ollama"] = "ollama"
    primary_model: str = ""
    fallback_model: str = ""

    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "production-api"
    
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    rate_limit: str = "20/minute"
    cache_ttl_seconds: int = 300
    max_retries: int = 3
    
    
    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def resolve_llm_settings(self) -> "Settings":
        if self.llm_provider == "google" and not self.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required when LLM_PROVIDER=google")

        default_primary, default_fallback = DEFAULT_MODELS[self.llm_provider]
        self.primary_model = self.primary_model or default_primary
        self.fallback_model = self.fallback_model or default_fallback
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"
    
@lru_cache
def get_settings() -> Settings:
    """Cached settings instance - loaded once, reused everywhere."""
    return Settings()

if __name__ == "__main__":
    settings = get_settings()
    print(f"Environment: {settings.app_env}")
    print(f"Primary model: {settings.primary_model}")
    print(f"Rate limit: {settings.rate_limit}")
    print(f"Cache TTL: {settings.cache_ttl_seconds}")
    print(f"Max retries: {settings.max_retries}")
    print(f"Is production: {settings.is_production}")
    print("Config loaded succesfully")
