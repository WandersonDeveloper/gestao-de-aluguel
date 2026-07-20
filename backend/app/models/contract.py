import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ContractStatus(str, enum.Enum):
    RASCUNHO = "rascunho"
    ATIVO = "ativo"
    VENCIDO = "vencido"
    ENCERRADO = "encerrado"
    CANCELADO = "cancelado"


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ContractStatus] = mapped_column(
        SAEnum(ContractStatus, name="contract_status"),
        default=ContractStatus.RASCUNHO,
        server_default=ContractStatus.RASCUNHO.name,
        nullable=False,
    )
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    observacoes: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
