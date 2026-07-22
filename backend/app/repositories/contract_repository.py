from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract import (
    OPEN_ENDED_SENTINEL_DATE,
    BillingPeriodicity,
    Contract,
    ContractSignatureStatus,
    ContractStatus,
    ContractType,
)


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
    db: Session,
    skip: int = 0,
    limit: int = 50,
    cliente_id: int | None = None,
    status=None,
    tipo: ContractType | None = None,
    assinatura_status: ContractSignatureStatus | None = None,
) -> list[Contract]:
    stmt = select(Contract)
    if cliente_id is not None:
        stmt = stmt.where(Contract.cliente_id == cliente_id)
    if status is not None:
        stmt = stmt.where(Contract.status == status)
    if tipo is not None:
        stmt = stmt.where(Contract.tipo == tipo)
    if assinatura_status is not None:
        stmt = stmt.where(Contract.assinatura_status == assinatura_status)
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


def delete(db: Session, contract: Contract) -> None:
    db.delete(contract)
    db.commit()


def list_aguardando_confirmacao(db: Session) -> list[Contract]:
    """Contratos aguardando resposta do cliente via WhatsApp (ver
    contract_signature_service) — tipicamente uma lista pequena a qualquer
    momento, então escanear todos é aceitável."""
    stmt = select(Contract).where(
        Contract.assinatura_status == ContractSignatureStatus.AGUARDANDO_CONFIRMACAO
    )
    return list(db.scalars(stmt))


def list_ativos_em_aberto_recorrentes(db: Session) -> list[Contract]:
    """Contratos ativos, sem data final (ver Contract.is_em_aberto), com
    periodicidade mensal/diária e valor_recorrente definido — candidatos ao
    job generate_next_recurring_invoices."""
    stmt = select(Contract).where(
        Contract.status == ContractStatus.ATIVO,
        Contract.data_fim >= OPEN_ENDED_SENTINEL_DATE,
        Contract.periodicidade_cobranca.in_([BillingPeriodicity.MENSAL, BillingPeriodicity.DIARIA]),
        Contract.valor_recorrente.isnot(None),
    )
    return list(db.scalars(stmt))
