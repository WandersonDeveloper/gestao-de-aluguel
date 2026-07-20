from sqlalchemy.orm import Session

from app.models.equipment_category import EquipmentCategory
from app.schemas.equipment_category import EquipmentCategoryCreate, EquipmentCategoryUpdate
from app.services import equipment_category_service


def create_category(db: Session, data: EquipmentCategoryCreate) -> EquipmentCategory:
    return equipment_category_service.create_category(db, data)


def get_category(db: Session, category_id: int) -> EquipmentCategory:
    return equipment_category_service.get_category(db, category_id)


def list_categories(db: Session, skip: int, limit: int) -> list[EquipmentCategory]:
    return equipment_category_service.list_categories(db, skip=skip, limit=limit)


def update_category(db: Session, category_id: int, data: EquipmentCategoryUpdate) -> EquipmentCategory:
    return equipment_category_service.update_category(db, category_id, data)


def delete_category(db: Session, category_id: int) -> None:
    equipment_category_service.delete_category(db, category_id)
