from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Cybercrime Investigation Platform"
    app_env: str = "development"
    app_secret_key: str = "development-only-secret-change-me"
    access_token_minutes: int = 480
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    admin_email: str = "admin@example.local"
    admin_password: str = "ChangeMeNow!123"
    admin_name: str = "Platform Administrator"

    database_url: str = (
        "postgresql+psycopg://cybercrime:cybercrime_dev_password@postgres:5432/cybercrime"
    )
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_secure: bool = False
    minio_evidence_bucket: str = "evidence"
    minio_report_bucket: str = "reports"

    opensearch_url: str = "http://opensearch:9200"
    opensearch_index: str = "normalized-events"
    opensearch_verify_certs: bool = False

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_dev_password"

    llm_provider: str = "none"
    llm_base_url: str = "http://host.docker.internal:11434/v1"
    llm_api_key: str = "local-development-key"
    llm_model: str = "qwen2.5:7b"
    llm_timeout_seconds: int = 90

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
