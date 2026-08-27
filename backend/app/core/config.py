from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: Literal["development", "staging", "production"] = "development"
    SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://metis:metis@localhost:5432/metis"
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Razorpay ──────────────────────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ── Groq / AI Agent ───────────────────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    # ── ML Models ─────────────────────────────────────────────────────────────
    ML_MODELS_DIR: str = "models"
    PROPENSITY_MODEL_PATH: str = ""
    INTERVENTION_MODEL_PATH: str = ""
    UPLIFT_MODEL_PATH: str = ""
    FATIGUE_MODEL_PATH: str = ""

    # ── MLflow ────────────────────────────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5050"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def use_ml_stubs(self) -> bool:
        """True when no trained model files are configured — falls back to rule-based stubs."""
        return not bool(self.PROPENSITY_MODEL_PATH and self.INTERVENTION_MODEL_PATH)


@lru_cache
def get_settings() -> Settings:
    return Settings()
