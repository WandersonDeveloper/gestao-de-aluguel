from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contract_amendment import ContractAmendment


def create(db: Session, data: dict) -> ContractAmendment:
    amendment = ContractAmendment(**data)
    db.add(amendment)
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
