from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import equipment_controller
from app.models.equipment import EquipmentStatus
from app.models.user import User
from app.schemas.equipment import EquipmentCreate, EquipmentRead, EquipmentUpdate
from app.schemas.inventory_movement import EquipmentStatusChange, InventoryMovementRead
from app.utils.deps import get_current_user

router = APIRouter(prefix="/equipment", tags=["equipment"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=EquipmentRead, status_code=status.HTTP_201_CREATED)
def create_equipment(data: EquipmentCreate, db: Session = Depends(get_db)) -> EquipmentRead:
    return equipment_controller.create_equipment(db, data)


@router.get("", response_model=list[EquipmentRead])
def list_equipment(
    skip: int = 0,
    limit: int = 50,
    categoria_id: int | None = None,
    status: EquipmentStatus | None = None,
    nome: str | None = None,
    db: Session = Depends(get_db),
) -> list[EquipmentRead]:
    return equipment_controller.list_equipment(db, skip, limit, categoria_id, status, nome)


@router.get("/{equipment_id}", response_model=EquipmentRead)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)) -> EquipmentRead:
    return equipment_controller.get_equipment(db, equipment_id)


@router.patch("/{equipment_id}", response_model=EquipmentRead)
def update_equipment(
    equipment_id: int, data: EquipmentUpdate, db: Session = Depends(get_db)
) -> EquipmentRead:
    return equipment_controller.update_equipment(db, equipment_id, data)


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)) -> None:
    equipment_controller.delete_equipment(db, equipment_id)


@router.post("/{equipment_id}/status", response_model=EquipmentRead)
def change_equipment_status(
    equipment_id: int,
    data: EquipmentStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EquipmentRead:
    return equipment_controller.change_status(db, equipment_id, data, current_user.id)


@router.get("/{equipment_id}/movements", response_model=list[InventoryMovementRead])
def list_equipment_movements(
    equipment_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)
) -> list[InventoryMovementRead]:
    return equipment_controller.list_movements(db, equipment_id, skip, limit)
