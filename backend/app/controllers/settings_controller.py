from sqlalchemy.orm import Session

from app.models.message_template import MessageTemplate, TemplateKey
from app.services import message_template_service, whatsapp_connection_service


def list_message_templates(db: Session) -> list[MessageTemplate]:
    return message_template_service.list_templates(db)


def update_message_template(db: Session, chave: TemplateKey, conteudo: str) -> MessageTemplate:
    return message_template_service.update_template(db, chave, conteudo)


def get_whatsapp_status() -> dict:
    return whatsapp_connection_service.get_status()


def connect_whatsapp() -> dict:
    return whatsapp_connection_service.connect()


def disconnect_whatsapp() -> None:
    whatsapp_connection_service.disconnect()
