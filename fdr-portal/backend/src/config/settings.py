"""
Configuration module - loads all settings from environment / .env file
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./fdr_portal.db"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8

    # Storage
    STORAGE_PATH: str = "./storage/uploads"

    # OCR
    OCR_MODE: str = "mock"  # "mock" | "tesseract"
    OCR_CONFIDENCE_THRESHOLD: float = 0.80

    # Demo clock override (ISO date string, e.g. "2026-11-01")
    DEMO_DATE: Optional[str] = None

    # Mail
    MAIL_ENABLED: bool = False
    MAIL_FROM: str = "noreply@demo.in"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 25

    # Alert intervals in days
    ALERT_DAYS: str = "90,30,15,7"

    # Rule thresholds (fallbacks)
    MIN_TENURE_DAYS: int = 365
    MIN_PRINCIPAL: int = 100000

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def alert_days_list(self) -> List[int]:
        return [int(d.strip()) for d in self.ALERT_DAYS.split(",")]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
