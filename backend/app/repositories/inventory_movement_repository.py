from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory_movement import InventoryMovement


def create(db: Session, data: dict) -> InventoryMovement:
    movement = InventoryMovement(**data)
    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement


def list_by_equipamento(
    db: Session,
    equipamento_id: int,
    skip: int = 0,
    limit: int = 50,
    desde: datetime | None = None,
) -> list[InventoryMovement]:
    stmt = select(InventoryMovement).where(InventoryMovement.equipamento_id == equipamento_id)
    if desde is not None:
        stmt = stmt.where(InventoryMovement.created_at >= desde)
    stmt = stmt.order_by(InventoryMovement.created_at.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))
