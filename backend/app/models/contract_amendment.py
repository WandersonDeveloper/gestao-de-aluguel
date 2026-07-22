import enum
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.contract import ContractSignatureStatus
from app.models.contract_item import ContractItem


class ContractAmendmentType(str, enum.Enum):
    EXTENSAO = "extensao"
    BAIXA_TOTAL = "baixa_total"
    BAIXA_PARCIAL = "baixa_parcial"
    CANCELAMENTO = "cancelamento"
    ADICAO_ITEM = "adicao_item"


class ContractAmendment(Base):
    __tablename__ = "contract_amendments"

    id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    tipo: Mapped[ContractAmendmentType] = mapped_column(
        SAEnum(ContractAmendmentType, name="contract_amendment_type"), nullable=False
    )
    data_anterior: Mapped[date | None] = mapped_column(Date)
    data_nova: Mapped[date | None] = mapped_column(Date)
    motivo: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Confirmação de aceite via WhatsApp específica deste aditivo (ver
    # contract_signature_service.enviar_confirmacao_aditivo) — só populado
    # quando tipo == ADICAO_ITEM, já que só a adição de item muda o valor do
    # contrato e por isso exige novo aceite do cliente. Mesmo padrão dos
    # campos assinatura_* de Contract, reaproveitando o mesmo enum.
    assinatura_status: Mapped[ContractSignatureStatus] = mapped_column(
        SAEnum(ContractSignatureStatus, name="contract_signature_status"),
        default=ContractSignatureStatus.NAO_ENVIADO,
        server_default=ContractSignatureStatus.NAO_ENVIADO.name,
        nullable=False,
    )
    assinatura_mensagem_enviada: Mapped[str | None] = mapped_column(String(2000))
    assinatura_enviada_em: Mapped[datetime | None] = mapped_column()
    assinatura_resposta_texto: Mapped[str | None] = mapped_column(String(500))
    assinatura_confirmada_em: Mapped[datetime | None] = mapped_column()
    assinatura_comprovante_key: Mapped[str | None] = mapped_column(String(255))

    # Itens criados por este aditivo (ver contract_service.add_items, que grava
    # amendment_id em cada ContractItem novo) — viewonly, só pra exibição no
    # histórico de aditivos, não substitui a lógica de negócio já existente.
    itens: Mapped[list[ContractItem]] = relationship(viewonly=True, order_by="ContractItem.id")
