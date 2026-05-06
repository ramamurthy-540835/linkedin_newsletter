from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LinkedIn Post Agent"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000

    gcp_project_id: str = ""
    gcp_region: str = "us-central1"
    firestore_collection_drafts: str = "linkedin_drafts"
    firestore_collection_posts: str = "linkedin_posts"
    firestore_collection_analytics: str = "linkedin_analytics"

    vertex_model: str = "gemini-2.5-flash"

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_redirect_uri: str = ""

    cloud_tasks_queue: str = "linkedin-post-schedule"
    cloud_tasks_location: str = "us-central1"
    cloud_run_base_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
