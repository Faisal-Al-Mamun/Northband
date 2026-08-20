from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../../.env"), extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://northband:northband@localhost:5432/northband"
    database_url_sync: str = "postgresql+psycopg://northband:northband@localhost:5432/northband"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_expire_minutes: int = 10080
    cors_origins: str = "http://localhost:3000"
    upload_dir: str = "./uploads"

    llm_default_provider: str = "openrouter"
    llm_default_model: str = "openai/gpt-4o-mini"
    llm_cheap_provider: str = ""
    llm_cheap_model: str = ""

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    openai_compat_api_key: str = ""
    openai_compat_base_url: str = "https://api.openai.com/v1"
    openai_compat_model: str = "gpt-4o-mini"

    stt_provider: str = "auto"
    whisper_model: str = "base"
    stt_device: str = "cpu"
    stt_compute_type: str = "int8"
    stt_warmup_on_start: bool = False

    agent_writing: str = ""
    agent_speaking: str = ""
    agent_grammar: str = ""
    agent_scoring: str = ""
    agent_feedback: str = ""
    agent_performance: str = ""
    agent_revision: str = ""
    agent_explain: str = ""

    scoring_llm_enabled: bool = False
    explain_llm_enabled: bool = True
    llm_timeout_seconds: float = 45.0
    agent_coach: str = ""
    agent_bank: str = ""

    # Listening TTS: pocket (Kyutai Pocket TTS) → macOS say. Never use sine tones.
    tts_engine: str = "auto"
    tts_warmup_on_start: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"prod", "production"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
