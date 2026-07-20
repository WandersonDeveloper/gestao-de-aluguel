from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.equipment import EquipmentStatus


class EquipmentStatusChange(BaseModel):
    status: EquipmentStatus
    motivo: str | None = None


class InventoryMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipamento_id: int
    usuario_id: int
    status_anterior: EquipmentStatus
    status_novo: EquipmentStatus
    motivo: str | None
    created_at: datetime
