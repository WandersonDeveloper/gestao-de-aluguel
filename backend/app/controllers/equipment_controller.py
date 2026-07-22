from sqlalchemy.orm import Session

from app.config.storage import get_file_url
from app.models.equipment import Equipment, EquipmentStatus
from app.models.equipment_stock import EquipmentStock
from app.models.inventory_movement import InventoryMovement
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.schemas.equipment_photo import EquipmentPhotoRead
from app.schemas.equipment_stock import EquipmentStockUpsert
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
    filial_id: int | None = None,
) -> list[Equipment]:
    return equipment_service.list_equipment(
        db, skip=skip, limit=limit, categoria_id=categoria_id, status=status, nome=nome, filial_id=filial_id
    )


def list_estoque(db: Session, equipment_id: int) -> list[EquipmentStock]:
    return equipment_service.list_estoque(db, equipment_id)


def set_estoque(db: Session, equipment_id: int, filial_id: int, data: EquipmentStockUpsert) -> EquipmentStock:
    return equipment_service.set_estoque(db, equipment_id, filial_id, data)


def remove_estoque(db: Session, equipment_id: int, filial_id: int) -> None:
    equipment_service.remove_estoque(db, equipment_id, filial_id)


def update_equipment(db: Session, equipment_id: int, data: EquipmentUpdate) -> Equipment:
    return equipment_service.update_equipment(db, equipment_id, data)


def delete_equipment(db: Session, equipment_id: int) -> None:
    equipment_service.delete_equipment(db, equipment_id)


def change_status(
    db: Session, equipment_id: int, data: EquipmentStatusChange, usuario_id: int
) -> Equipment:
    return equipment_service.change_status(db, equipment_id, data, usuario_id)


def list_movements(
    db: Session, equipment_id: int, skip: int, limit: int, dias: int | None = 30
) -> list[InventoryMovement]:
    return equipment_service.list_movements(db, equipment_id, skip=skip, limit=limit, dias=dias)


def add_photo(
    db: Session, equipment_id: int, file_bytes: bytes, filename: str, content_type: str | None
) -> EquipmentPhotoRead:
    key = equipment_service.add_photo(db, equipment_id, file_bytes, filename, content_type)
    return EquipmentPhotoRead(key=key, url=get_file_url(key))


def list_photos(db: Session, equipment_id: int) -> list[EquipmentPhotoRead]:
    keys = equipment_service.list_photo_keys(db, equipment_id)
    return [EquipmentPhotoRead(key=key, url=get_file_url(key)) for key in keys]


def remove_photo(db: Session, equipment_id: int, key: str) -> None:
    equipment_service.remove_photo(db, equipment_id, key)
