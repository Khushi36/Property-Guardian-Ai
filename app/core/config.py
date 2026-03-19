from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Property Fraud Detection System"
    # Update this with your actual Postgres credentials
    # Updated to load from .env. If not set, it will raise an error (unless empty strings are bypassed by validation).
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/property_db"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"
    DOCUMENT_STORAGE_PATH: str = "./data/documents"
    OPENROUTER_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "arcee-ai/trinity-large-preview:free"
    REDIS_URL: Optional[str] = None

    # Email Settings for OTP
    SMTP_SERVER: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""

    # Security — SECRET_KEY MUST be set in .env (no default = fail if missing)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALLOWED_ORIGINS: str = (
        '["http://localhost:8501", "http://localhost:8000"]'  # JSON string format
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
