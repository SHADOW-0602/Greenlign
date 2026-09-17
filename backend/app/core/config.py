from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Neon serverless Postgres — must include ?sslmode=require
    database_url: str

    redis_url: str = "redis://redis:6379/0"

    # Object storage — S3-compatible API used for both MinIO (local) and Backblaze B2 (prod).
    # Switch environments by changing these four env vars; application code never changes.
    s3_endpoint_url: str = "http://minio:9000"     # MinIO local; B2: https://s3.<region>.backblazeb2.com
    s3_access_key: str = "minioadmin"              # B2 keyID
    s3_secret_key: str = "minioadmin"              # B2 applicationKey
    s3_bucket_name: str = "greenlign-raw"

    secret_key: str = "change-me-in-production"
    environment: str = "development"               # "development" | "production"

    # Groq LLM (Phase 2+) — optional in Phase 0 but validated when present
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    classification_confidence_threshold: float = 0.75

    @field_validator("database_url")
    @classmethod
    def database_url_must_have_ssl(cls, v: str) -> str:
        """Fail fast if someone accidentally points at a local Postgres without SSL."""
        if "sslmode" not in v and "sqlite" not in v:
            raise ValueError(
                "DATABASE_URL must include ?sslmode=require for Neon. "
                "Example: postgresql+asyncpg://user:pass@host/db?sslmode=require"
            )
        return v


settings = Settings()
