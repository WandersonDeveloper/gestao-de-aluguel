from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError
from app.domain.invoice_state import assert_valid_transition
from app.models.invoice import InvoiceStatus
from app.models.payment import Payment
from app.repositories import invoice_repository, payment_repository
from app.schemas.payment import PaymentCreate
from app.services import invoice_service


def register_payment(db: Session, invoice_id: int, data: PaymentCreate, usuario_id: int) -> Payment:
    invoice = invoice_service.get_invoice(db, invoice_id)
    if invoice.status not in (InvoiceStatus.PENDENTE, InvoiceStatus.ATRASADA):
        raise ConflictError(
            f"Não é possível registrar pagamento em fatura com status {invoice.status.value}"
        )
    if data.valor <= 0:
        raise ConflictError("O valor do pagamento deve ser positivo")

    payment = payment_repository.create(
        db,
        {
            "invoice_id": invoice_id,
            "usuario_id": usuario_id,
            "valor": data.valor,
            "forma_pagamento": data.forma_pagamento,
            "observacoes": data.observacoes,
        },
    )

    total_pago = payment_repository.total_paid(db, invoice_id)
    if total_pago >= invoice.valor:
        assert_valid_transition(invoice.status, InvoiceStatus.PAGA)
        invoice_repository.update(db, invoice, {"status": InvoiceStatus.PAGA})

    db.commit()
    db.refresh(payment)
    return payment


def list_payments(db: Session, invoice_id: int) -> list[Payment]:
    invoice_service.get_invoice(db, invoice_id)
    return payment_repository.list_by_invoice(db, invoice_id)
