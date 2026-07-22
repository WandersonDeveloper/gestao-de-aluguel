from datetime import date

from sqlalchemy import func, select
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


def delete_by_contrato(db: Session, contrato_id: int) -> None:
    for item in list_by_contrato(db, contrato_id):
        db.delete(item)
    db.flush()


def exists_for_equipamento(db: Session, equipamento_id: int) -> bool:
    stmt = select(ContractItem.id).where(ContractItem.equipamento_id == equipamento_id).limit(1)
    return db.scalar(stmt) is not None


def exists_for_filial(db: Session, filial_id: int) -> bool:
    stmt = select(ContractItem.id).where(ContractItem.filial_id == filial_id).limit(1)
    return db.scalar(stmt) is not None


def list_ativos_by_equipamento_filial(db: Session, equipamento_id: int, filial_id: int) -> list[ContractItem]:
    stmt = select(ContractItem).where(
        ContractItem.equipamento_id == equipamento_id,
        ContractItem.filial_id == filial_id,
        ContractItem.status == ContractItemStatus.ATIVO,
    )
    return list(db.scalars(stmt))


def sum_quantidade_ativa_overlap(
    db: Session,
    equipamento_id: int,
    filial_id: int,
    data_inicio: date,
    data_fim: date,
    excluir_item_id: int | None = None,
) -> int:
    """Soma a quantidade reservada por itens ATIVOS desse par (equipamento,
    filial) cujo período se sobrepõe a [data_inicio, data_fim]. Usado para
    checar se ainda há estoque disponível antes de reservar mais (ver
    contract_service) — a checagem é sempre por filial, já que o mesmo
    equipamento pode ter estoques independentes em filiais diferentes."""
    stmt = select(func.coalesce(func.sum(ContractItem.quantidade), 0)).where(
        ContractItem.equipamento_id == equipamento_id,
        ContractItem.filial_id == filial_id,
        ContractItem.status == ContractItemStatus.ATIVO,
        ContractItem.data_inicio_item <= data_fim,
        ContractItem.data_fim_item >= data_inicio,
    )
    if excluir_item_id is not None:
        stmt = stmt.where(ContractItem.id != excluir_item_id)
    return db.scalar(stmt) or 0
