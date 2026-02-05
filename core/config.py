from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Environment variables take precedence; .env.local overrides .env for local defaults.
    model_config = SettingsConfigDict(env_file=(".env", ".env.local"), extra="ignore")

    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    kb_path: str = "./kb/subjects.yaml"
    catalog_path: str = "./catalog/instances.yaml"
    enable_persistence: bool = False
    trace_file: str | None = None
    database_url: str | None = None
    live_mode: bool = False
    show_demo_data: bool = True

settings = Settings()
