from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract import Contract, ContractStatus


def create(db: Session, data: dict) -> Contract:
    # Sem commit aqui de propósito: a criação de contrato envolve múltiplas
    # linhas (contrato + itens) que precisam ser confirmadas atomicamente
    # pelo service (ver app/services/contract_service.py).
    contract = Contract(**data)
    db.add(contract)
    db.flush()
    return contract


def get(db: Session, contract_id: int) -> Contract | None:
    return db.get(Contract, contract_id)


def list_all(
    db: Session, skip: int = 0, limit: int = 50, cliente_id: int | None = None, status=None
) -> list[Contract]:
    stmt = select(Contract)
    if cliente_id is not None:
        stmt = stmt.where(Contract.cliente_id == cliente_id)
    if status is not None:
        stmt = stmt.where(Contract.status == status)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update(db: Session, contract: Contract, data: dict) -> Contract:
    for field, value in data.items():
        setattr(contract, field, value)
    db.flush()
    return contract


def list_expirable(db: Session, hoje: date) -> list[Contract]:
    stmt = select(Contract).where(Contract.status == ContractStatus.ATIVO, Contract.data_fim < hoje)
    return list(db.scalars(stmt))
