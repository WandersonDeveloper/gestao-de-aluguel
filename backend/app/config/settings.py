from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Gestao de Alugueis API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://alugueis:alugueis@localhost:5432/alugueis"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60


settings = Settings()
