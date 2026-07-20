from sqlalchemy.orm import Session

from app.models.service_order import ServiceOrder, ServiceOrderStatus
from app.schemas.service_order import ServiceOrderCreate
from app.services import service_order_service


def create_service_order(db: Session, data: ServiceOrderCreate) -> ServiceOrder:
    return service_order_service.create_service_order(db, data)


def get_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    return service_order_service.get_service_order(db, service_order_id)


def list_service_orders(
    db: Session,
    skip: int,
    limit: int,
    equipamento_id: int | None,
    contrato_id: int | None,
    status: ServiceOrderStatus | None,
) -> list[ServiceOrder]:
    return service_order_service.list_service_orders(
        db, skip=skip, limit=limit, equipamento_id=equipamento_id, contrato_id=contrato_id, status=status
    )


def start_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    return service_order_service.start_service_order(db, service_order_id)


def complete_service_order(db: Session, service_order_id: int, observacoes: str | None, usuario_id: int) -> ServiceOrder:
    return service_order_service.complete_service_order(db, service_order_id, observacoes, usuario_id)


def cancel_service_order(db: Session, service_order_id: int, observacoes: str | None, usuario_id: int) -> ServiceOrder:
    return service_order_service.cancel_service_order(db, service_order_id, observacoes, usuario_id)
