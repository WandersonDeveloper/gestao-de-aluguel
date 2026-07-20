from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceStatus
from app.models.invoice_item import InvoiceItem
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate
from app.services import invoice_service, payment_service


def get_invoice(db: Session, invoice_id: int) -> Invoice:
    return invoice_service.get_invoice(db, invoice_id)


def list_invoices(
    db: Session, skip: int, limit: int, contrato_id: int | None, status: InvoiceStatus | None
) -> list[Invoice]:
    return invoice_service.list_invoices(db, skip=skip, limit=limit, contrato_id=contrato_id, status=status)


def list_invoice_items(db: Session, invoice_id: int) -> list[InvoiceItem]:
    return invoice_service.list_invoice_items(db, invoice_id)


def cancel_invoice(db: Session, invoice_id: int) -> Invoice:
    return invoice_service.cancel_invoice(db, invoice_id)


def register_payment(db: Session, invoice_id: int, data: PaymentCreate, usuario_id: int) -> Payment:
    return payment_service.register_payment(db, invoice_id, data, usuario_id)


def list_payments(db: Session, invoice_id: int) -> list[Payment]:
    return payment_service.list_payments(db, invoice_id)
