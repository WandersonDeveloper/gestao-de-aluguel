from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base
from app.models.equipment import EquipmentStatus


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status_anterior: Mapped[EquipmentStatus] = mapped_column(
        SAEnum(EquipmentStatus, name="equipment_status"), nullable=False
    )
    status_novo: Mapped[EquipmentStatus] = mapped_column(
        SAEnum(EquipmentStatus, name="equipment_status"), nullable=False
    )
    motivo: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
