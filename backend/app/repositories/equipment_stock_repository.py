from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.equipment_stock import EquipmentStock


def get(db: Session, equipamento_id: int, filial_id: int) -> EquipmentStock | None:
    stmt = select(EquipmentStock).where(
        EquipmentStock.equipamento_id == equipamento_id, EquipmentStock.filial_id == filial_id
    )
    return db.scalar(stmt)


def get_for_update(db: Session, equipamento_id: int, filial_id: int) -> EquipmentStock | None:
    """Busca travando a linha (SELECT ... FOR UPDATE) — usado ao reservar
    quantidade de um equipamento numa filial, para serializar requisições
    concorrentes sobre o mesmo par (equipamento, filial)."""
    stmt = (
        select(EquipmentStock)
        .where(EquipmentStock.equipamento_id == equipamento_id, EquipmentStock.filial_id == filial_id)
        .with_for_update()
    )
    return db.scalar(stmt)


def list_by_equipamento(db: Session, equipamento_id: int) -> list[EquipmentStock]:
    stmt = select(EquipmentStock).where(EquipmentStock.equipamento_id == equipamento_id)
    return list(db.scalars(stmt))


def exists_for_filial(db: Session, filial_id: int) -> bool:
    stmt = select(EquipmentStock.id).where(EquipmentStock.filial_id == filial_id).limit(1)
    return db.scalar(stmt) is not None


def upsert(db: Session, equipamento_id: int, filial_id: int, data: dict) -> EquipmentStock:
    estoque = get(db, equipamento_id, filial_id)
    if estoque is None:
        estoque = EquipmentStock(equipamento_id=equipamento_id, filial_id=filial_id, **data)
        db.add(estoque)
    else:
        for field, value in data.items():
            setattr(estoque, field, value)
    db.commit()
    db.refresh(estoque)
    return estoque


def delete(db: Session, estoque: EquipmentStock) -> None:
    db.delete(estoque)
    db.commit()
