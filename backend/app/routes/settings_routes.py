from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import settings_controller
from app.models.message_template import TemplateKey
from app.models.user import User, UserRole
from app.schemas.message_template import MessageTemplateRead, MessageTemplateUpdate
from app.schemas.whatsapp_connection import WhatsappConnectRead, WhatsappStatusRead
from app.utils.deps import get_current_user, require_roles

router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_user), Depends(require_roles(UserRole.ADMIN))],
)


@router.get("/message-templates", response_model=list[MessageTemplateRead])
def list_message_templates(db: Session = Depends(get_db)) -> list[MessageTemplateRead]:
    return settings_controller.list_message_templates(db)


@router.put("/message-templates/{chave}", response_model=MessageTemplateRead)
def update_message_template(
    chave: TemplateKey, data: MessageTemplateUpdate, db: Session = Depends(get_db)
) -> MessageTemplateRead:
    return settings_controller.update_message_template(db, chave, data.conteudo)


@router.get("/whatsapp/status", response_model=WhatsappStatusRead)
def get_whatsapp_status() -> WhatsappStatusRead:
    return settings_controller.get_whatsapp_status()


@router.post("/whatsapp/connect", response_model=WhatsappConnectRead)
def connect_whatsapp() -> WhatsappConnectRead:
    return settings_controller.connect_whatsapp()


@router.post("/whatsapp/disconnect", status_code=204)
def disconnect_whatsapp() -> None:
    settings_controller.disconnect_whatsapp()
