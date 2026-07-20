from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    forma_pagamento: Mapped[str | None] = mapped_column(String(50))
    observacoes: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
