from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.config.storage import get_file_url
from app.models.equipment import EquipmentStatus
from app.schemas.equipment_stock import EquipmentStockRead


class EquipmentBase(BaseModel):
    nome: str
    categoria_id: int
    marca: str | None = None
    modelo: str | None = None
    identificador: str | None = None
    localizacao: str | None = None
    observacoes: str | None = None
    atributos_extra: dict = {}


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    # `status` não é editável aqui de propósito: a transição de estado passa pela
    # máquina de estado em app/domain/equipment_state.py (ver rota /equipment/{id}/status).
    # Estoque/valores por filial também não são editáveis aqui — ver
    # POST/DELETE /equipment/{id}/estoque/{filial_id}.
    nome: str | None = None
    categoria_id: int | None = None
    marca: str | None = None
    modelo: str | None = None
    identificador: str | None = None
    localizacao: str | None = None
    observacoes: str | None = None
    atributos_extra: dict | None = None


class EquipmentRead(EquipmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: EquipmentStatus
    quantidade_total: int
    estoques: list[EquipmentStockRead] = []
    fotos: list[str] = Field(default_factory=list, exclude=True)
    created_at: datetime

    @computed_field
    @property
    def foto_principal_url(self) -> str | None:
        return get_file_url(self.fotos[0]) if self.fotos else None
