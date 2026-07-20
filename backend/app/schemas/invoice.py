from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.invoice import InvoiceStatus


class InvoiceItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    contract_item_id: int
    valor: Decimal


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contrato_id: int
    data_vencimento: date
    valor: Decimal
    status: InvoiceStatus
    multa_juros_aplicado: Decimal | None
    numero_nota_fiscal: str | None
    created_at: datetime


class InvoiceWithItemsRead(InvoiceRead):
    itens: list[InvoiceItemRead]


class InvoiceCancelRequest(BaseModel):
    motivo: str | None = None
