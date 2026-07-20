from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import service_order_controller
from app.models.service_order import ServiceOrderStatus
from app.models.user import User, UserRole
from app.schemas.service_order import ServiceOrderCloseRequest, ServiceOrderCreate, ServiceOrderRead
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/service-orders", tags=["service-orders"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ServiceOrderRead, status_code=status.HTTP_201_CREATED)
def create_service_order(
    data: ServiceOrderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ServiceOrderRead:
    return service_order_controller.create_service_order(db, data)


@router.get("", response_model=list[ServiceOrderRead])
def list_service_orders(
    skip: int = 0,
    limit: int = 50,
    equipamento_id: int | None = None,
    contrato_id: int | None = None,
    status: ServiceOrderStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ServiceOrderRead]:
    return service_order_controller.list_service_orders(db, skip, limit, equipamento_id, contrato_id, status)


@router.get("/{service_order_id}", response_model=ServiceOrderRead)
def get_service_order(service_order_id: int, db: Session = Depends(get_db)) -> ServiceOrderRead:
    return service_order_controller.get_service_order(db, service_order_id)


@router.post("/{service_order_id}/start", response_model=ServiceOrderRead)
def start_service_order(
    service_order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ServiceOrderRead:
    return service_order_controller.start_service_order(db, service_order_id)


@router.post("/{service_order_id}/complete", response_model=ServiceOrderRead)
def complete_service_order(
    service_order_id: int,
    data: ServiceOrderCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ServiceOrderRead:
    return service_order_controller.complete_service_order(db, service_order_id, data.observacoes, current_user.id)


@router.post("/{service_order_id}/cancel", response_model=ServiceOrderRead)
def cancel_service_order(
    service_order_id: int,
    data: ServiceOrderCloseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ServiceOrderRead:
    return service_order_controller.cancel_service_order(db, service_order_id, data.observacoes, current_user.id)
