from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment import Payment


def create(db: Session, data: dict) -> Payment:
    payment = Payment(**data)
    db.add(payment)
    db.flush()
    return payment


def list_by_invoice(db: Session, invoice_id: int) -> list[Payment]:
    stmt = select(Payment).where(Payment.invoice_id == invoice_id)
    return list(db.scalars(stmt))


def total_paid(db: Session, invoice_id: int):
    stmt = select(func.coalesce(func.sum(Payment.valor), 0)).where(Payment.invoice_id == invoice_id)
    return db.scalar(stmt)
