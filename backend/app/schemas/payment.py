from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    valor: Decimal
    forma_pagamento: str | None = None
    observacoes: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    usuario_id: int
    valor: Decimal
    forma_pagamento: str | None
    observacoes: str | None
    created_at: datetime
