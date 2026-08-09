from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = (
        "postgresql+asyncpg://enterprise_rag:CHANGE_ME@postgres:5432/enterprise_rag"
    )

    jwt_secret_key: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=60, gt=0)

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimension: int = Field(default=384, gt=0)

    chunk_target_tokens: int = 400
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 60
    chunk_min_tokens: int = 40

    retrieval_top_k: int = 6
    chat_history_message_limit: int = 8

    max_pdf_size_mb: int = 20
    upload_directory: Path = Path("/app/uploads")
    frontend_origin: str = "http://localhost:3000"

    # Offline RAGAS evaluation
    ragas_enabled: bool = False
    ragas_evaluator_model: str = "gemini-2.0-flash"
    ragas_max_concurrency: int = Field(default=2, gt=0)
    ragas_cache_directory: Path = Path(".cache/ragas")
    ragas_evaluator_timeout_seconds: float = Field(default=60.0, gt=0)

    @model_validator(mode="after")
    def chunk_bounds(self):
        if not (
            self.chunk_min_tokens
            <= self.chunk_target_tokens
            <= self.chunk_max_tokens
        ):
            raise ValueError(
                "chunk token settings must satisfy min <= target <= max"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()