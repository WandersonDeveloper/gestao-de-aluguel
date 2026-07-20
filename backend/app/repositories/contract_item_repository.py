from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract_item import ContractItem, ContractItemStatus


def create(db: Session, data: dict) -> ContractItem:
    item = ContractItem(**data)
    db.add(item)
    db.flush()
    return item


def get(db: Session, item_id: int) -> ContractItem | None:
    return db.get(ContractItem, item_id)


def list_by_contrato(db: Session, contrato_id: int) -> list[ContractItem]:
    stmt = select(ContractItem).where(ContractItem.contrato_id == contrato_id)
    return list(db.scalars(stmt))


def list_ativos_by_contrato(db: Session, contrato_id: int) -> list[ContractItem]:
    stmt = select(ContractItem).where(
        ContractItem.contrato_id == contrato_id, ContractItem.status == ContractItemStatus.ATIVO
    )
    return list(db.scalars(stmt))


def update(db: Session, item: ContractItem, data: dict) -> ContractItem:
    for field, value in data.items():
        setattr(item, field, value)
    db.flush()
    return item


def exists_for_equipamento(db: Session, equipamento_id: int) -> bool:
    stmt = select(ContractItem.id).where(ContractItem.equipamento_id == equipamento_id).limit(1)
    return db.scalar(stmt) is not None
