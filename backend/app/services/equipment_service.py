from sqlalchemy.orm import Session

from app.config import storage
from app.domain.equipment_state import assert_valid_transition
from app.domain.exceptions import ConflictError, NotFoundError
from app.models.equipment import Equipment, EquipmentStatus
from app.repositories import (
    contract_item_repository,
    equipment_category_repository,
    equipment_repository,
    inventory_movement_repository,
    service_order_repository,
)
from app.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.schemas.inventory_movement import EquipmentStatusChange


def _ensure_categoria_exists(db: Session, categoria_id: int) -> None:
    if equipment_category_repository.get(db, categoria_id) is None:
        raise NotFoundError(f"Categoria {categoria_id} não encontrada")


def create_equipment(db: Session, data: EquipmentCreate) -> Equipment:
    _ensure_categoria_exists(db, data.categoria_id)
    if data.identificador and equipment_repository.get_by_identificador(db, data.identificador):
        raise ConflictError(f"Já existe um equipamento com o identificador {data.identificador}")
    return equipment_repository.create(db, data.model_dump())


def get_equipment(db: Session, equipment_id: int) -> Equipment:
    equipment = equipment_repository.get(db, equipment_id)
    if equipment is None:
        raise NotFoundError(f"Equipamento {equipment_id} não encontrado")
    return equipment


def list_equipment(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    categoria_id: int | None = None,
    status: EquipmentStatus | None = None,
    nome: str | None = None,
) -> list[Equipment]:
    return equipment_repository.list_all(
        db, skip=skip, limit=limit, categoria_id=categoria_id, status=status, nome=nome
    )


def update_equipment(db: Session, equipment_id: int, data: EquipmentUpdate) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    updates = data.model_dump(exclude_unset=True)
    if "categoria_id" in updates:
        _ensure_categoria_exists(db, updates["categoria_id"])
    if "identificador" in updates and updates["identificador"] != equipment.identificador:
        existing = equipment_repository.get_by_identificador(db, updates["identificador"])
        if existing is not None:
            raise ConflictError(f"Já existe um equipamento com o identificador {updates['identificador']}")
    return equipment_repository.update(db, equipment, updates)


def delete_equipment(db: Session, equipment_id: int) -> None:
    equipment = get_equipment(db, equipment_id)
    if inventory_movement_repository.list_by_equipamento(db, equipment_id, limit=1):
        raise ConflictError(
            "Não é possível excluir um equipamento com histórico de movimentação registrado"
        )
    if contract_item_repository.exists_for_equipamento(db, equipment_id):
        raise ConflictError("Não é possível excluir um equipamento vinculado a algum contrato")
    if service_order_repository.exists_for_equipamento(db, equipment_id):
        raise ConflictError("Não é possível excluir um equipamento com ordens de serviço registradas")

    fotos = list(equipment.fotos)
    equipment_repository.delete(db, equipment)
    for key in fotos:
        storage.delete_file(key)


def change_status(
    db: Session, equipment_id: int, data: EquipmentStatusChange, usuario_id: int
) -> Equipment:
    equipment = get_equipment(db, equipment_id)
    assert_valid_transition(equipment.status, data.status)

    status_anterior = equipment.status
    equipment = equipment_repository.update(db, equipment, {"status": data.status})
    inventory_movement_repository.create(
        db,
        {
            "equipamento_id": equipment.id,
            "usuario_id": usuario_id,
            "status_anterior": status_anterior,
            "status_novo": data.status,
            "motivo": data.motivo,
        },
    )
    return equipment


def list_movements(db: Session, equipment_id: int, skip: int = 0, limit: int = 50):
    get_equipment(db, equipment_id)
    return inventory_movement_repository.list_by_equipamento(db, equipment_id, skip=skip, limit=limit)


def add_photo(db: Session, equipment_id: int, file_bytes: bytes, filename: str, content_type: str | None) -> str:
    equipment = get_equipment(db, equipment_id)
    key = storage.upload_file(file_bytes, filename, content_type)
    equipment_repository.update(db, equipment, {"fotos": [*equipment.fotos, key]})
    return key


def list_photo_keys(db: Session, equipment_id: int) -> list[str]:
    equipment = get_equipment(db, equipment_id)
    return list(equipment.fotos)


def remove_photo(db: Session, equipment_id: int, key: str) -> None:
    equipment = get_equipment(db, equipment_id)
    if key not in equipment.fotos:
        raise NotFoundError(f"Foto {key} não encontrada para este equipamento")
    equipment_repository.update(db, equipment, {"fotos": [k for k in equipment.fotos if k != key]})
    storage.delete_file(key)
