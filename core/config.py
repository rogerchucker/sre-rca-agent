from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str
    openai_model: str = "gpt-4.1-mini"
    kb_path: str = "./kb/subjects.yaml"
    enable_persistence: bool = False
    trace_file: str | None = None

settings = Settings()
