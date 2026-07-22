from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class EquipmentStockUpsert(BaseModel):
    """Corpo de POST /equipment/{id}/estoque/{filial_id} — filial_id vem da URL."""

    quantidade: int = Field(default=1, ge=1)
    valor_diario: Decimal | None = None
    valor_mensal: Decimal | None = None
    valor_hora: Decimal | None = None


class EquipmentStockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipamento_id: int
    filial_id: int
    quantidade: int
    valor_diario: Decimal | None
    valor_mensal: Decimal | None
    valor_hora: Decimal | None
