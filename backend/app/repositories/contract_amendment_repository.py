from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract import ContractSignatureStatus
from app.models.contract_amendment import ContractAmendment


def create(db: Session, data: dict) -> ContractAmendment:
    amendment = ContractAmendment(**data)
    db.add(amendment)
    db.flush()
    return amendment


def get(db: Session, amendment_id: int) -> ContractAmendment | None:
    return db.get(ContractAmendment, amendment_id)


def update(db: Session, amendment: ContractAmendment, data: dict) -> ContractAmendment:
    for field, value in data.items():
        setattr(amendment, field, value)
    db.flush()
    return amendment


def list_by_contrato(db: Session, contrato_id: int, skip: int = 0, limit: int = 50) -> list[ContractAmendment]:
    stmt = (
        select(ContractAmendment)
        .where(ContractAmendment.contrato_id == contrato_id)
        .order_by(ContractAmendment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.scalars(stmt))


def list_aguardando_confirmacao(db: Session) -> list[ContractAmendment]:
    """Aditivos aguardando resposta do cliente via WhatsApp (ver
    contract_signature_service) — mesmo padrão de contract_repository.
    list_aguardando_confirmacao, mas para a confirmação por aditivo."""
    stmt = select(ContractAmendment).where(
        ContractAmendment.assinatura_status == ContractSignatureStatus.AGUARDANDO_CONFIRMACAO
    )
    return list(db.scalars(stmt))
