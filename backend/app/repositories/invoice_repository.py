from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus


def create(db: Session, data: dict) -> Invoice:
    invoice = Invoice(**data)
    db.add(invoice)
    db.flush()
    return invoice


def get(db: Session, invoice_id: int) -> Invoice | None:
    return db.get(Invoice, invoice_id)


def list_all(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    contrato_id: int | None = None,
    status: InvoiceStatus | None = None,
) -> list[Invoice]:
    stmt = select(Invoice)
    if contrato_id is not None:
        stmt = stmt.where(Invoice.contrato_id == contrato_id)
    if status is not None:
        stmt = stmt.where(Invoice.status == status)
    stmt = stmt.order_by(Invoice.data_vencimento).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def list_by_contrato(db: Session, contrato_id: int) -> list[Invoice]:
    stmt = select(Invoice).where(Invoice.contrato_id == contrato_id)
    return list(db.scalars(stmt))


def list_pendentes_vencidas(db: Session, hoje: date) -> list[Invoice]:
    stmt = select(Invoice).where(Invoice.status == InvoiceStatus.PENDENTE, Invoice.data_vencimento < hoje)
    return list(db.scalars(stmt))


def update(db: Session, invoice: Invoice, data: dict) -> Invoice:
    for field, value in data.items():
        setattr(invoice, field, value)
    db.flush()
    return invoice
