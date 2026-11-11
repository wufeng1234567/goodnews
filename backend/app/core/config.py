"""Application settings.

All infrastructure and secret values come from the repository-root .env file.
The .env file is intentionally git-ignored; see .env.example for the complete
variable catalogue.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote_plus

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py -> core -> app -> backend -> repository root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    """Typed runtime configuration.

    Environment variable names are case-insensitive and map directly to the
    field names (for example ``LLM_MODEL`` -> ``llm_model``).
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "goodnews"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # PostgreSQL ---------------------------------------------------------
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "goodnews"
    postgres_user: str = "goodnews"
    postgres_password: SecretStr = SecretStr("goodnews")
    database_url: str | None = None
    database_enabled: bool = True
    database_echo: bool = False

    # Redis (cache only in the MVP) -------------------------------------
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True
    cache_ttl_seconds: int = 300

    # Neo4j --------------------------------------------------------------
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("goodnews_neo4j_dev")
    neo4j_database: str = "neo4j"
    neo4j_enabled: bool = True

    # OpenAI-compatible LLM ---------------------------------------------
    deepseek_api_key: SecretStr = SecretStr("")
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"
    llm_timeout_seconds: float = 90.0
    llm_max_retries: int = 2
    llm_temperature: float = 0.1
    llm_max_tokens: int = 3500
    llm_json_repair_attempts: int = 1

    # Fact-check graph ---------------------------------------------------
    factcheck_max_evidence_rounds: int = 2
    max_claims: int = 6
    max_article_chars: int = 24_000
    max_factcheck_input_chars: int = 50_000
    evidence_fetch_top_n: int = 3

    # Search / crawler ---------------------------------------------------
    search_provider: Literal["bing_rss", "google_news_rss"] = "google_news_rss"
    search_result_limit: int = 8
    search_timeout_seconds: float = 20.0
    crawler_timeout_seconds: int = 45
    crawler_playwright_enabled: bool = True
    playwright_timeout_ms: int = 20_000
    # "msedge" reuses the system Edge (recommended on Windows); leave empty
    # after running ``playwright install chromium`` to use Playwright's browser.
    playwright_browser_channel: str = "msedge"
    allow_private_urls: bool = False

    # Social platforms ---------------------------------------------------
    social_browser_headless: bool = True
    social_browser_timeout_ms: int = 45_000
    social_state_dir: str = "backend/.browser-profiles"
    social_max_comments_default: int = 30
    social_login_timeout_seconds: int = 600
    social_keepalive_hours: int = 6
    social_full_max_comments: int = 100_000
    # Optional raw Cookie headers. Prefer the login helper which writes a
    # Playwright storage-state file; these values are only for deployment.
    xhs_cookie: SecretStr = SecretStr("")
    douyin_cookie: SecretStr = SecretStr("")
    bilibili_cookie: SecretStr = SecretStr("")

    @field_validator("llm_temperature")
    @classmethod
    def validate_temperature(cls, value: float) -> float:
        if not 0 <= value <= 2:
            raise ValueError("llm_temperature must be between 0 and 2")
        return value

    @field_validator("factcheck_max_evidence_rounds")
    @classmethod
    def validate_rounds(cls, value: int) -> int:
        if not 0 <= value <= 3:
            raise ValueError("factcheck_max_evidence_rounds must be between 0 and 3")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Return an async SQLAlchemy DSN, preferring an explicit override."""
        if self.database_url:
            return self.database_url
        password = quote_plus(self.postgres_password.get_secret_value())
        user = quote_plus(self.postgres_user)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def llm_api_key(self) -> str:
        return self.deepseek_api_key.get_secret_value()

    @property
    def social_state_path(self) -> Path:
        state_dir = Path(self.social_state_dir)
        if not state_dir.is_absolute():
            state_dir = PROJECT_ROOT / state_dir
        return state_dir.resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Tests may call get_settings.cache_clear()."""
    return Settings()
