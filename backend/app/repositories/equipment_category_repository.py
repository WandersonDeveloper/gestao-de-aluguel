from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment_category import EquipmentCategory


def create(db: Session, data: dict) -> EquipmentCategory:
    category = EquipmentCategory(**data)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def get(db: Session, category_id: int) -> EquipmentCategory | None:
    return db.get(EquipmentCategory, category_id)


def get_by_nome(db: Session, nome: str) -> EquipmentCategory | None:
    return db.scalar(select(EquipmentCategory).where(EquipmentCategory.nome == nome))


def list_all(db: Session, skip: int = 0, limit: int = 50) -> list[EquipmentCategory]:
    stmt = select(EquipmentCategory).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update(db: Session, category: EquipmentCategory, data: dict) -> EquipmentCategory:
    for field, value in data.items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete(db: Session, category: EquipmentCategory) -> None:
    db.delete(category)
    db.commit()
