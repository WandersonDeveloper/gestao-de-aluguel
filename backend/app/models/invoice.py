import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class InvoiceStatus(str, enum.Enum):
    PENDENTE = "pendente"
    PAGA = "paga"
    ATRASADA = "atrasada"
    CANCELADA = "cancelada"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    data_vencimento: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(InvoiceStatus, name="invoice_status"),
        default=InvoiceStatus.PENDENTE,
        server_default=InvoiceStatus.PENDENTE.name,
        nullable=False,
    )
    multa_juros_aplicado: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    numero_nota_fiscal: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
