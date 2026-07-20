from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Gestao de Alugueis API"
    environment: str = "development"

    database_url: str = "postgresql+psycopg2://alugueis:alugueis@localhost:5432/alugueis"

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60

    s3_endpoint_url: str = "http://localhost:9000"
    # Endpoint usado só para gerar presigned URLs (precisa ser resolvível pelo
    # navegador/cliente externo — dentro do docker-compose isso é diferente do
    # hostname interno "minio" usado para as chamadas backend -> MinIO).
    s3_public_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "alugueis"
    s3_secret_key: str = "alugueis123"
    s3_bucket_name: str = "equipment-photos"


settings = Settings()
