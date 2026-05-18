from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_ENV_LOCAL = Path(__file__).resolve().parents[3] / ".env.local"
BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "LinkedIn Post Generator"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8007

    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    disable_gcp: bool = False
    disable_bigquery: bool = False
    disable_vertex_ai: bool = False
    local_dev_mode: bool = False
    local_db_path: str = "backend/data/content_studio.db"

    vertex_ai_model: str = ""
    ai_provider: str = "auto"

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = ""
    linkedin_author_urn: str = ""
    linkedin_access_token: str = ""

    twitter_api_key: str = ""
    twitter_api_secret: str = ""

    facebook_app_id: str = ""
    facebook_app_secret: str = ""

    medium_api_key: str = ""
    devto_api_key: str = ""

    serp_api_key: str = ""
    openai_api_key: str = ""
    xai_api_key: str = ""
    xai_base_url: str = ""
    xai_model: str = ""
    xai_image_model: str = ""
    xai_video_model: str = ""
    xai_monthly_budget_usd: float = 5.0
    xai_soft_stop_usd: float = 4.0
    xai_hard_stop_usd: float = 5.0
    xai_auto_reload_enabled: bool = False
    xai_auto_reload_threshold_usd: float = 0.0
    xai_auto_reload_amount_usd: float = 0.0
    xai_absolute_hard_stop_usd: float = 100.0

    # 44-char URL-safe base64 Fernet key; if empty a deterministic dev key is used
    credentials_encryption_key: str = ""

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_ENV), str(ROOT_ENV_LOCAL)),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
