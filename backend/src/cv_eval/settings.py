from pydantic_settings import BaseSettings, SettingsConfigDict

from .extraction import OcrMode


class Settings(BaseSettings):
    """CV_EVAL_* environment variables or .env. PydanticAI reads GOOGLE_API_KEY itself."""

    model_config = SettingsConfigDict(env_prefix="CV_EVAL_", env_file=".env", extra="ignore")

    model: str = "google:gemini-3.8-flash"
    ocr: OcrMode = "auto"
    cors_origins: list[str] = ["http://localhost:3000"]
