import enum
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ContractAmendmentType(str, enum.Enum):
    EXTENSAO = "extensao"
    BAIXA_TOTAL = "baixa_total"
    BAIXA_PARCIAL = "baixa_parcial"
    CANCELAMENTO = "cancelamento"


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
