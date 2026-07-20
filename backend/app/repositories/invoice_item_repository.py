from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice_item import InvoiceItem


def create(db: Session, data: dict) -> InvoiceItem:
    item = InvoiceItem(**data)
    db.add(item)
    db.flush()
    return item


def list_by_invoice(db: Session, invoice_id: int) -> list[InvoiceItem]:
    stmt = select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
    return list(db.scalars(stmt))
