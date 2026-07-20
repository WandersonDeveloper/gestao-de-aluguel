from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.equipment import EquipmentStatus


class EquipmentBase(BaseModel):
    nome: str
    categoria_id: int
    marca: str | None = None
    modelo: str | None = None
    identificador: str | None = None
    valor_diario: Decimal | None = None
    valor_mensal: Decimal | None = None
    localizacao: str | None = None
    observacoes: str | None = None
    atributos_extra: dict = {}


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    # `status` não é editável aqui de propósito: a transição de estado passa pela
    # máquina de estado em app/domain/equipment_state.py (ver rota /equipment/{id}/status).
    nome: str | None = None
    categoria_id: int | None = None
    marca: str | None = None
    modelo: str | None = None
    identificador: str | None = None
    valor_diario: Decimal | None = None
    valor_mensal: Decimal | None = None
    localizacao: str | None = None
    observacoes: str | None = None
    atributos_extra: dict | None = None


class EquipmentRead(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: EquipmentStatus
    created_at: datetime
