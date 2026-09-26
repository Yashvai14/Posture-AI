from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Defaults that were published in earlier versions of this code base and must never be used.
KNOWN_INSECURE_SECRETS = {"super-secret-key-change-in-production-1234567890"}


class Settings(BaseSettings):
    """Application settings. Required values have no defaults so startup fails fast when missing."""

    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    PROJECT_NAME: str = "PostureAI"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: SecretStr = Field(min_length=32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=720, ge=5, le=60 * 24 * 7)
    CORS_ORIGINS: str = "http://localhost:3000"
    RATE_LIMIT_ENABLED: bool = True

    # Database (PostgreSQL only)
    DATABASE_URL: str

    # Storage and uploads
    STORAGE_DIR: Path = BACKEND_DIR / "storage"
    MAX_UPLOAD_MB: int = Field(default=10, ge=1, le=50)
    MAX_IMAGE_PIXELS: int = 40_000_000

    # Posture model
    POSE_MODEL_PATH: Path = BACKEND_DIR / "models" / "pose_landmarker_full.task"

    # Background jobs: "thread" runs analyses on a worker pool, "inline" runs them in the request (tests)
    JOB_MODE: Literal["thread", "inline"] = "thread"
    JOB_WORKERS: int = Field(default=2, ge=1, le=16)

    # Ollama (optional local LLM)
    OLLAMA_ENABLED: bool = True
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=90.0, gt=0)
    OLLAMA_MAX_RETRIES: int = Field(default=1, ge=0, le=3)

    # Provider discovery (OpenStreetMap)
    PROVIDER_DISCOVERY_ENABLED: bool = True
    OVERPASS_URL: str = "https://overpass-api.de/api/interpreter"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"
    HTTP_USER_AGENT: str = "PostureAI/2.0 (posture screening app; contact: admin@example.com)"
    PROVIDER_CACHE_DAYS: int = Field(default=7, ge=1)
    DEFAULT_SEARCH_RADIUS_KM: float = 30.0
    MAX_SEARCH_RADIUS_KM: float = 50.0
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # Appointments
    BOOKING_WINDOW_DAYS: int = 60
    BOOKING_MIN_LEAD_MINUTES: int = 30

    @field_validator("DATABASE_URL")
    @classmethod
    def require_postgres(cls, value: str) -> str:
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("DATABASE_URL must be a PostgreSQL URL; other databases are not supported")
        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def reject_placeholder_secret(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value().lower()
        if "change-me" in secret or secret in KNOWN_INSECURE_SECRETS:
            raise ValueError("SECRET_KEY is a placeholder or a publicly known default; generate a new random value")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
