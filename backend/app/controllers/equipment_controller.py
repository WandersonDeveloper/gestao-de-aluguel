from sqlalchemy.orm import Session

from app.models.equipment import Equipment, EquipmentStatus
from app.models.inventory_movement import InventoryMovement
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.schemas.inventory_movement import EquipmentStatusChange
from app.services import equipment_service


def create_equipment(db: Session, data: EquipmentCreate) -> Equipment:
    return equipment_service.create_equipment(db, data)


def get_equipment(db: Session, equipment_id: int) -> Equipment:
    return equipment_service.get_equipment(db, equipment_id)


def list_equipment(
    db: Session,
    skip: int,
    limit: int,
    categoria_id: int | None,
    status: EquipmentStatus | None,
    nome: str | None,
) -> list[Equipment]:
    return equipment_service.list_equipment(
        db, skip=skip, limit=limit, categoria_id=categoria_id, status=status, nome=nome
    )


def update_equipment(db: Session, equipment_id: int, data: EquipmentUpdate) -> Equipment:
    return equipment_service.update_equipment(db, equipment_id, data)


def delete_equipment(db: Session, equipment_id: int) -> None:
    equipment_service.delete_equipment(db, equipment_id)


def change_status(
    db: Session, equipment_id: int, data: EquipmentStatusChange, usuario_id: int
) -> Equipment:
    return equipment_service.change_status(db, equipment_id, data, usuario_id)


def list_movements(db: Session, equipment_id: int, skip: int, limit: int) -> list[InventoryMovement]:
    return equipment_service.list_movements(db, equipment_id, skip=skip, limit=limit)
