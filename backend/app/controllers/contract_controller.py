from sqlalchemy.orm import Session

from app.models.contract import Contract, ContractStatus
from app.models.contract_amendment import ContractAmendment
from app.models.contract_item import ContractItem
from app.schemas.contract import ContractCreate
from app.services import contract_service


def create_contract(db: Session, data: ContractCreate) -> Contract:
    return contract_service.create_contract(db, data)


def get_contract(db: Session, contract_id: int) -> Contract:
    return contract_service.get_contract(db, contract_id)


def list_contracts(
    db: Session, skip: int, limit: int, cliente_id: int | None, status: ContractStatus | None
) -> list[Contract]:
    return contract_service.list_contracts(db, skip=skip, limit=limit, cliente_id=cliente_id, status=status)


def list_items(db: Session, contract_id: int) -> list[ContractItem]:
    return contract_service.list_items(db, contract_id)


def activate_contract(db: Session, contract_id: int, usuario_id: int) -> Contract:
    return contract_service.activate_contract(db, contract_id, usuario_id)


def dar_baixa(
    db: Session, contract_id: int, item_ids: list[int] | None, motivo: str | None, usuario_id: int
) -> Contract:
    return contract_service.dar_baixa(db, contract_id, item_ids, motivo, usuario_id)


def extend_contract(db: Session, contract_id: int, nova_data_fim, motivo: str | None, usuario_id: int) -> Contract:
    return contract_service.extend_contract(db, contract_id, nova_data_fim, motivo, usuario_id)


def cancel_contract(db: Session, contract_id: int, motivo: str | None, usuario_id: int) -> Contract:
    return contract_service.cancel_contract(db, contract_id, motivo, usuario_id)


def list_amendments(db: Session, contract_id: int, skip: int, limit: int) -> list[ContractAmendment]:
    return contract_service.list_amendments(db, contract_id, skip=skip, limit=limit)
