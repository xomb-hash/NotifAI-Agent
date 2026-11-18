"""Application settings loaded from environment / .env."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google Gemini / GenAI
    google_api_key: str = Field(..., validation_alias="GOOGLE_API_KEY")
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite", validation_alias="GEMINI_MODEL"
    )
    gemini_embedding_model: str = Field(
        default="text-embedding-004", validation_alias="GEMINI_EMBEDDING_MODEL"
    )

    # Vector Store (Chroma)
    chroma_host: str = Field(default="localhost", validation_alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, validation_alias="CHROMA_PORT")
    chroma_collection: str = Field(
        default="notifai_notices", validation_alias="CHROMA_COLLECTION"
    )

    # Google Calendar
    google_calendar_credentials: str = Field(
        default="./langcredentials.json",
        validation_alias="GOOGLE_CALENDAR_CREDENTIALS",
    )
    google_calendar_token: str = Field(
        default="./token.json", validation_alias="GOOGLE_CALENDAR_TOKEN"
    )
    google_calendar_id: str = Field(
        default="primary", validation_alias="GOOGLE_CALENDAR_ID"
    )

    # API Server
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8080, validation_alias="API_PORT")
    api_key: str | None = Field(default=None, validation_alias="API_KEY")

    # Observability
    otel_endpoint: str | None = Field(default=None, validation_alias="OTEL_ENDPOINT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # RAG Settings
    chunk_size: int = Field(default=500, validation_alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, validation_alias="CHUNK_OVERLAP")
    top_k: int = Field(default=5, validation_alias="TOP_K")
    relevance_threshold: float = Field(default=0.7, validation_alias="RELEVANCE_THRESHOLD")

    # Cost Tracking (USD per 1M tokens, as of Nov 2026)
    gemini_input_cost_per_m: float = Field(
        default=0.30, validation_alias="GEMINI_INPUT_COST_PER_M"
    )
    gemini_output_cost_per_m: float = Field(
        default=2.50, validation_alias="GEMINI_OUTPUT_COST_PER_M"
    )
    gemini_embedding_cost_per_m: float = Field(
        default=0.02, validation_alias="GEMINI_EMBEDDING_COST_PER_M"
    )

    # Rate Limiting
    rate_limit_requests: int = Field(default=100, validation_alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, validation_alias="RATE_LIMIT_WINDOW")

    # Multi-Agent
    max_validation_retries: int = Field(
        default=2, validation_alias="MAX_VALIDATION_RETRIES"
    )
    agent_temperature: float = Field(default=0.0, validation_alias="AGENT_TEMPERATURE")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
