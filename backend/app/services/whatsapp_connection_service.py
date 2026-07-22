from app.config import whatsapp
from app.config.settings import settings


def get_status() -> dict:
    state = whatsapp.get_connection_state()
    if state is None:
        return {"existe": False, "estado": None}
    return {"existe": True, "estado": state.get("instance", {}).get("state")}


def _configurar_webhook() -> None:
    url = f"{settings.backend_internal_url}/api/webhooks/whatsapp/{settings.whatsapp_webhook_secret}"
    whatsapp.set_webhook(url, ["MESSAGES_UPSERT"])


def connect() -> dict:
    state = whatsapp.get_connection_state()
    if state is None:
        resultado = whatsapp.create_instance()
        instance = resultado.get("instance", {})
        qrcode = resultado.get("qrcode", {})
        _configurar_webhook()
        return {"estado": instance.get("status"), "qrcode_base64": qrcode.get("base64")}

    qrcode = whatsapp.fetch_qrcode() or {}
    _configurar_webhook()
    return {
        "estado": state.get("instance", {}).get("state"),
        "qrcode_base64": qrcode.get("base64"),
    }


def disconnect() -> None:
    whatsapp.logout_instance()
