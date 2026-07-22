"""Cliente da Evolution API — sempre falamos com a Evolution API, nunca
diretamente com a Meta. A Evolution API já sabe conversar tanto com o WhatsApp
não-oficial (Baileys, QR code) quanto com a API oficial (Cloud API da Meta,
"WHATSAPP-BUSINESS") por baixo dos panos, dependendo de como a instância foi
criada — então `send_text`/`send_document`/etc. não mudam em nada entre os
dois casos, só o corpo de `POST /instance/create` (ver `create_instance`)."""

import httpx

from app.config.settings import settings
from app.domain.exceptions import ExternalServiceError


def normalize_phone_br(telefone: str) -> str:
    digits = "".join(ch for ch in telefone if ch.isdigit())
    if not digits.startswith("55"):
        digits = f"55{digits}"
    return digits


def _request(method: str, url: str, json: dict | None = None) -> dict | None:
    try:
        response = httpx.request(
            method,
            url,
            json=json,
            headers={"apikey": settings.evolution_api_key},
            timeout=30.0,
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json() if response.content else None
    except httpx.HTTPStatusError as exc:
        raise ExternalServiceError(
            f"Evolution API retornou erro {exc.response.status_code} em {url}"
        ) from exc
    except httpx.HTTPError as exc:
        raise ExternalServiceError(f"Falha ao conectar com a Evolution API: {exc}") from exc


def _instance_request(method: str, path: str, json: dict | None = None) -> dict | None:
    """Para endpoints no formato {path}/{instance} (a maioria — sendText, sendMedia,
    connectionState, connect, logout)."""
    url = f"{settings.evolution_api_url}/{path}/{settings.evolution_instance_name}"
    return _request(method, url, json)


def send_text(phone: str, message: str) -> None:
    _instance_request("POST", "message/sendText", {"number": normalize_phone_br(phone), "text": message})


def send_document(phone: str, base64_content: str, filename: str, caption: str) -> None:
    _instance_request(
        "POST",
        "message/sendMedia",
        {
            "number": normalize_phone_br(phone),
            "mediatype": "document",
            "mimetype": "application/pdf",
            "media": base64_content,
            "fileName": filename,
            "caption": caption,
        },
    )


def get_connection_state() -> dict | None:
    """Retorna o estado da instância (ex.: {"instance": {"state": "open"}}), ou
    None se a instância ainda não foi criada na Evolution API."""
    return _instance_request("GET", "instance/connectionState")


def _usa_api_oficial() -> bool:
    return bool(settings.meta_whatsapp_token and settings.meta_whatsapp_number_id)


def create_instance() -> dict:
    """Cria a instância. Diferente dos outros endpoints, /instance/create não
    leva o nome da instância na URL (vai no corpo), por isso usa _request em
    vez de _instance_request.

    Se as credenciais da API oficial (`META_WHATSAPP_TOKEN`/`META_WHATSAPP_NUMBER_ID`)
    estiverem configuradas, cria a instância no modo "WHATSAPP-BUSINESS" (a
    própria Evolution API fala com a Cloud API da Meta por baixo — sem QR code,
    token permanente do Business Manager). Caso contrário, cria no modo Baileys
    de sempre (QR code). Em ambos os casos, o resto da API da Evolution
    (`send_text`, `send_document`, etc.) funciona exatamente igual."""
    body: dict = {"instanceName": settings.evolution_instance_name}
    if _usa_api_oficial():
        body.update(
            {
                "qrcode": False,
                "integration": "WHATSAPP-BUSINESS",
                "token": settings.meta_whatsapp_token,
                "number": settings.meta_whatsapp_number_id,
                "businessId": settings.meta_whatsapp_business_id,
            }
        )
    else:
        body.update({"qrcode": True, "integration": "WHATSAPP-BAILEYS"})

    return _request("POST", f"{settings.evolution_api_url}/instance/create", body)


def fetch_qrcode() -> dict | None:
    """Busca um QR code novo para uma instância já existente — resposta tem o
    QR code em `base64` (sem wrapper), formato diferente de /instance/create.
    Não se aplica a instâncias no modo "WHATSAPP-BUSINESS" (sem QR/pareamento
    — o número já vem verificado pela Meta Business Manager)."""
    return _instance_request("GET", "instance/connect")


def logout_instance() -> None:
    _instance_request("DELETE", "instance/logout")


def set_webhook(url: str, events: list[str]) -> None:
    """Configura o webhook da instância — payload confirmado ao vivo contra
    uma instância real (POST /webhook/set/{instance})."""
    _instance_request(
        "POST",
        "webhook/set",
        {"webhook": {"url": url, "enabled": True, "webhookByEvents": False, "events": events}},
    )
