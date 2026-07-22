from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment import Equipment, EquipmentStatus
from app.models.equipment_stock import EquipmentStock


def create(db: Session, data: dict) -> Equipment:
    equipment = Equipment(**data)
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def get(db: Session, equipment_id: int) -> Equipment | None:
    return db.get(Equipment, equipment_id)


def get_by_identificador(db: Session, identificador: str) -> Equipment | None:
    return db.scalar(select(Equipment).where(Equipment.identificador == identificador))


def list_all(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    categoria_id: int | None = None,
    status: EquipmentStatus | None = None,
    nome: str | None = None,
    filial_id: int | None = None,
) -> list[Equipment]:
    stmt = select(Equipment)
    if categoria_id is not None:
        stmt = stmt.where(Equipment.categoria_id == categoria_id)
    if status is not None:
        stmt = stmt.where(Equipment.status == status)
    if nome:
        stmt = stmt.where(Equipment.nome.ilike(f"%{nome}%"))
    if filial_id is not None:
        stmt = stmt.where(
            Equipment.id.in_(select(EquipmentStock.equipamento_id).where(EquipmentStock.filial_id == filial_id))
        )
    stmt = stmt.distinct().offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update(db: Session, equipment: Equipment, data: dict) -> Equipment:
    for field, value in data.items():
        setattr(equipment, field, value)
    db.commit()
    db.refresh(equipment)
    return equipment


def delete(db: Session, equipment: Equipment) -> None:
    db.delete(equipment)
    db.commit()
