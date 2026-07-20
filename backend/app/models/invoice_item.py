from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    contract_item_id: Mapped[int] = mapped_column(ForeignKey("contract_items.id"), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
