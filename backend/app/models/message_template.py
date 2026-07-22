import enum
from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class TemplateKey(str, enum.Enum):
    COBRANCA_FATURA = "cobranca_fatura"
    CONTRATO_ASSINATURA = "contrato_assinatura"
    ACEITE_CONFIRMADO = "aceite_confirmado"
    ACEITE_RECUSADO = "aceite_recusado"
    ADITIVO_CONFIRMACAO = "aditivo_confirmacao"
    ADITIVO_ACEITE_CONFIRMADO = "aditivo_aceite_confirmado"
    ADITIVO_ACEITE_RECUSADO = "aditivo_aceite_recusado"


class MessageTemplate(Base):
    __tablename__ = "message_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[TemplateKey] = mapped_column(
        SAEnum(TemplateKey, name="template_key"), unique=True, nullable=False
    )
    conteudo: Mapped[str] = mapped_column(String(2000), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
