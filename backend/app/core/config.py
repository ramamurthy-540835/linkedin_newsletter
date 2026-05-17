from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LinkedIn Post Generator"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8007

    gcp_project_id: str = ""
    gcp_region: str = "us-central1"

    vertex_model: str = "gemini-2.5-flash"

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

    # 44-char URL-safe base64 Fernet key; if empty a deterministic dev key is used
    credentials_encryption_key: str = ""

    frontend_url: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
