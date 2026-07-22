from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.message_template import TemplateKey


class MessageTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chave: TemplateKey
    conteudo: str
    updated_at: datetime


class MessageTemplateUpdate(BaseModel):
    conteudo: str
