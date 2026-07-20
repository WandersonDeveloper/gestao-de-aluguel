from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.service_order import ServiceOrder, ServiceOrderStatus

OPEN_STATUSES = (ServiceOrderStatus.ABERTA, ServiceOrderStatus.EM_ANDAMENTO)


def create(db: Session, data: dict) -> ServiceOrder:
    service_order = ServiceOrder(**data)
    db.add(service_order)
    db.commit()
    db.refresh(service_order)
    return service_order


def get(db: Session, service_order_id: int) -> ServiceOrder | None:
    return db.get(ServiceOrder, service_order_id)


def get_open_by_equipamento(db: Session, equipamento_id: int) -> ServiceOrder | None:
    stmt = select(ServiceOrder).where(
        ServiceOrder.equipamento_id == equipamento_id, ServiceOrder.status.in_(OPEN_STATUSES)
    )
    return db.scalar(stmt)


def list_all(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    equipamento_id: int | None = None,
    contrato_id: int | None = None,
    status: ServiceOrderStatus | None = None,
) -> list[ServiceOrder]:
    stmt = select(ServiceOrder)
    if equipamento_id is not None:
        stmt = stmt.where(ServiceOrder.equipamento_id == equipamento_id)
    if contrato_id is not None:
        stmt = stmt.where(ServiceOrder.contrato_id == contrato_id)
    if status is not None:
        stmt = stmt.where(ServiceOrder.status == status)
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update(db: Session, service_order: ServiceOrder, data: dict) -> ServiceOrder:
    for field, value in data.items():
        setattr(service_order, field, value)
    db.commit()
    db.refresh(service_order)
    return service_order


def exists_for_equipamento(db: Session, equipamento_id: int) -> bool:
    stmt = select(ServiceOrder.id).where(ServiceOrder.equipamento_id == equipamento_id).limit(1)
    return db.scalar(stmt) is not None
