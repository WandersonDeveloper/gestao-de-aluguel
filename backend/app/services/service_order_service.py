from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.service_order_state import assert_valid_transition
from app.models.equipment import EquipmentStatus
from app.models.service_order import ServiceOrder, ServiceOrderStatus
from app.repositories import contract_repository, equipment_repository, service_order_repository
from app.schemas.inventory_movement import EquipmentStatusChange
from app.schemas.service_order import ServiceOrderCreate
from app.services import equipment_service


def _get_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = service_order_repository.get(db, service_order_id)
    if service_order is None:
        raise NotFoundError(f"Ordem de serviço {service_order_id} não encontrada")
    return service_order


def create_service_order(db: Session, data: ServiceOrderCreate) -> ServiceOrder:
    if equipment_repository.get(db, data.equipamento_id) is None:
        raise NotFoundError(f"Equipamento {data.equipamento_id} não encontrado")
    if data.contrato_id is not None and contract_repository.get(db, data.contrato_id) is None:
        raise NotFoundError(f"Contrato {data.contrato_id} não encontrado")
    if service_order_repository.get_open_by_equipamento(db, data.equipamento_id) is not None:
        raise ConflictError(
            f"Equipamento {data.equipamento_id} já possui uma ordem de serviço em aberto"
        )

    try:
        return service_order_repository.create(db, data.model_dump())
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"Equipamento {data.equipamento_id} já possui uma ordem de serviço em aberto"
        ) from exc


def get_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    return _get_service_order(db, service_order_id)


def list_service_orders(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    equipamento_id: int | None = None,
    contrato_id: int | None = None,
    status: ServiceOrderStatus | None = None,
) -> list[ServiceOrder]:
    return service_order_repository.list_all(
        db, skip=skip, limit=limit, equipamento_id=equipamento_id, contrato_id=contrato_id, status=status
    )


def start_service_order(db: Session, service_order_id: int) -> ServiceOrder:
    service_order = _get_service_order(db, service_order_id)
    assert_valid_transition(service_order.status, ServiceOrderStatus.EM_ANDAMENTO)
    return service_order_repository.update(db, service_order, {"status": ServiceOrderStatus.EM_ANDAMENTO})


def _release_equipment_if_in_maintenance(
    db: Session, equipamento_id: int, usuario_id: int, motivo: str
) -> None:
    equipamento = equipment_repository.get(db, equipamento_id)
    if equipamento is not None and equipamento.status == EquipmentStatus.MANUTENCAO:
        equipment_service.change_status(
            db, equipamento_id, EquipmentStatusChange(status=EquipmentStatus.DISPONIVEL, motivo=motivo), usuario_id
        )


def complete_service_order(
    db: Session, service_order_id: int, observacoes: str | None, usuario_id: int
) -> ServiceOrder:
    service_order = _get_service_order(db, service_order_id)
    assert_valid_transition(service_order.status, ServiceOrderStatus.CONCLUIDA)

    service_order = service_order_repository.update(
        db,
        service_order,
        {
            "status": ServiceOrderStatus.CONCLUIDA,
            "observacoes": observacoes,
            "data_conclusao": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )
    _release_equipment_if_in_maintenance(
        db, service_order.equipamento_id, usuario_id, f"Conclusão da OS {service_order.id}"
    )
    return service_order


def cancel_service_order(
    db: Session, service_order_id: int, observacoes: str | None, usuario_id: int
) -> ServiceOrder:
    service_order = _get_service_order(db, service_order_id)
    assert_valid_transition(service_order.status, ServiceOrderStatus.CANCELADA)

    service_order = service_order_repository.update(
        db,
        service_order,
        {
            "status": ServiceOrderStatus.CANCELADA,
            "observacoes": observacoes,
            "data_conclusao": datetime.now(timezone.utc).replace(tzinfo=None),
        },
    )
    _release_equipment_if_in_maintenance(
        db, service_order.equipamento_id, usuario_id, f"Cancelamento da OS {service_order.id}"
    )
    return service_order
