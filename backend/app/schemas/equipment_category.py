from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EquipmentCategoryBase(BaseModel):
    nome: str
    descricao: str | None = None


class EquipmentCategoryCreate(EquipmentCategoryBase):
    pass


class EquipmentCategoryUpdate(BaseModel):
    nome: str | None = None
    descricao: str | None = None


class EquipmentCategoryRead(EquipmentCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
