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
    show_demo_data: bool = False
    onboarding_profile: str = "template"
    onboarding_template_catalog_path: str = "./catalog/seeds/template.instances.yaml"
    onboarding_template_kb_path: str = "./kb/seeds/template.subjects.yaml"
    onboarding_demo_catalog_path: str = "./catalog/seeds/demo.instances.yaml"
    onboarding_demo_kb_path: str = "./kb/seeds/demo.subjects.yaml"
    rca_tools_schema_path: str = "./catalog/rca-tools.schema.yaml"

settings = Settings()
