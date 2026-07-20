from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import invoice_controller
from app.models.invoice import InvoiceStatus
from app.models.user import User, UserRole
from app.schemas.invoice import InvoiceItemRead, InvoiceRead
from app.schemas.payment import PaymentCreate, PaymentRead
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/invoices", tags=["invoices"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    skip: int = 0,
    limit: int = 50,
    contrato_id: int | None = None,
    status: InvoiceStatus | None = None,
    db: Session = Depends(get_db),
) -> list[InvoiceRead]:
    return invoice_controller.list_invoices(db, skip, limit, contrato_id, status)


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)) -> InvoiceRead:
    return invoice_controller.get_invoice(db, invoice_id)


@router.get("/{invoice_id}/items", response_model=list[InvoiceItemRead])
def list_invoice_items(invoice_id: int, db: Session = Depends(get_db)) -> list[InvoiceItemRead]:
    return invoice_controller.list_invoice_items(db, invoice_id)


@router.post("/{invoice_id}/cancel", response_model=InvoiceRead)
def cancel_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCEIRO)),
) -> InvoiceRead:
    return invoice_controller.cancel_invoice(db, invoice_id)


@router.post("/{invoice_id}/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def register_payment(
    invoice_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.FINANCEIRO)),
) -> PaymentRead:
    return invoice_controller.register_payment(db, invoice_id, data, current_user.id)


@router.get("/{invoice_id}/payments", response_model=list[PaymentRead])
def list_payments(invoice_id: int, db: Session = Depends(get_db)) -> list[PaymentRead]:
    return invoice_controller.list_payments(db, invoice_id)
