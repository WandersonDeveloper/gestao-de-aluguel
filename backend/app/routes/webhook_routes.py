from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.controllers import webhook_controller
from app.domain.exceptions import NotFoundError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/whatsapp/{secret}")
def receive_whatsapp_webhook(secret: str, payload: dict, db: Session = Depends(get_db)) -> dict:
    if secret != settings.whatsapp_webhook_secret:
        raise NotFoundError("Não encontrado")
    webhook_controller.process_whatsapp_webhook(db, payload)
    return {"status": "ok"}
