from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Property Fraud Detection System"
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/property_db"
    CHROMA_PERSIST_DIRECTORY: str = "./data/chroma_db"
    DOCUMENT_STORAGE_PATH: str = "./data/documents"
    OPENROUTER_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "arcee-ai/trinity-large-preview:free"
    REDIS_URL: Optional[str] = "redis://redis:6379/0"
    CHROMA_HOST: str = "chroma"
    CHROMA_PORT: int = 8000

    # Read-Only DB credentials (for SQL Explorer sandbox)
    READONLY_DB_USER: str = "read_only_user"
    READONLY_DB_PASSWORD: str = "readonly_password"

    # Neo4j Graph Database
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "password123"

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

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
