from sqlalchemy.orm import Session

from app.services import contract_signature_service


def process_whatsapp_webhook(db: Session, payload: dict) -> None:
    contract_signature_service.processar_webhook(db, payload)
