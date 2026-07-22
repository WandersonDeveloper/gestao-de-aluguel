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

    # Multa aplicada uma única vez quando uma fatura pendente vence (fluxo 5.5 do plano).
    late_fee_percentage: float = 2.0

    # Dados do locador/prestador usados no documento de contrato gerado em PDF
    # (ver contract_document_service). Sobrescrever via .env em produção.
    company_name: str = "[Razão social não configurada]"
    company_document: str = "[CNPJ não configurado]"
    company_address: str = "[Endereço não configurado]"

    # Integração com WhatsApp via Evolution API (ver docs/regras-de-negocio.md).
    evolution_api_url: str = "http://evolution-api:8080"
    evolution_api_key: str = "change-me"
    evolution_instance_name: str = "gestao-alugueis"

    # Credenciais da API oficial (Cloud API da Meta) — opcionais. Quando
    # preenchidas, a Evolution API cria a instância no modo "WHATSAPP-BUSINESS"
    # (fala com a Cloud API da Meta por baixo, sem QR code) em vez do modo
    # Baileys padrão (QR code). Ver app/config/whatsapp.py::create_instance.
    meta_whatsapp_token: str = ""
    meta_whatsapp_number_id: str = ""
    meta_whatsapp_business_id: str = ""

    # Webhook de confirmação de assinatura (ver contract_signature_service):
    # hostname interno pelo qual a Evolution API alcança o backend dentro da
    # rede Docker (mesmo padrão do S3_ENDPOINT_URL) + segredo na URL do
    # webhook, já que a Evolution API não assina o payload por HMAC.
    backend_internal_url: str = "http://backend:8000"
    whatsapp_webhook_secret: str = "change-me"


settings = Settings()
