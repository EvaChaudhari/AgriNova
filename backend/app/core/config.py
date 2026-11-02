"""Krishi Mitra Application Configuration.

Loads environment variables, default paths, and service endpoints.
"""

from typing import Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Krishi Mitra Agricultural Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Storage and Database
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/storage/krishi_mitra.db"

    # API Keys & External Providers
    GEMINI_API_KEY: Optional[str] = None
    BHASHINI_API_KEY: Optional[str] = None
    BHASHINI_USER_ID: Optional[str] = None
    OPENWEATHERMAP_API_KEY: Optional[str] = None
    SENTINEL_STAC_URL: str = "https://earth-search.aws.element84.com/v1"
    
    # Operational Envelope
    DEFAULT_LANGUAGE: str = "hi"
    SUPPORTED_LANGUAGES: list[str] = ["hi", "te", "mr", "en"]
    ENVIRONMENT: str = "development"

    # Security & Cryptographic Tokens
    JWT_SECRET_KEY: str = "agrinova-insecure-dev-secret-key-for-testing-only-replace-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days validity

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

