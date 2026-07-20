from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import contract_controller
from app.models.contract import ContractStatus
from app.models.user import User, UserRole
from app.schemas.contract import (
    ContractBaixaRequest,
    ContractCancelRequest,
    ContractCreate,
    ContractExtendRequest,
    ContractItemRead,
    ContractRead,
    ContractWithItemsRead,
)
from app.schemas.contract_amendment import ContractAmendmentRead
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/contracts", tags=["contracts"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ContractRead, status_code=status.HTTP_201_CREATED)
def create_contract(
    data: ContractCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ContractRead:
    return contract_controller.create_contract(db, data)


@router.get("", response_model=list[ContractRead])
def list_contracts(
    skip: int = 0,
    limit: int = 50,
    cliente_id: int | None = None,
    status: ContractStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ContractRead]:
    return contract_controller.list_contracts(db, skip, limit, cliente_id, status)


@router.get("/{contract_id}", response_model=ContractWithItemsRead)
def get_contract(contract_id: int, db: Session = Depends(get_db)) -> ContractWithItemsRead:
    contract = contract_controller.get_contract(db, contract_id)
    itens = contract_controller.list_items(db, contract_id)
    return ContractWithItemsRead(
        **ContractRead.model_validate(contract).model_dump(),
        itens=[ContractItemRead.model_validate(item) for item in itens],
    )


@router.post("/{contract_id}/activate", response_model=ContractRead)
def activate_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ContractRead:
    return contract_controller.activate_contract(db, contract_id, current_user.id)


@router.post("/{contract_id}/baixa", response_model=ContractRead)
def dar_baixa(
    contract_id: int,
    data: ContractBaixaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ContractRead:
    return contract_controller.dar_baixa(db, contract_id, data.item_ids, data.motivo, current_user.id)


@router.post("/{contract_id}/extend", response_model=ContractRead)
def extend_contract(
    contract_id: int,
    data: ContractExtendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ContractRead:
    return contract_controller.extend_contract(db, contract_id, data.nova_data_fim, data.motivo, current_user.id)


@router.post("/{contract_id}/cancel", response_model=ContractRead)
def cancel_contract(
    contract_id: int,
    data: ContractCancelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ContractRead:
    return contract_controller.cancel_contract(db, contract_id, data.motivo, current_user.id)


@router.get("/{contract_id}/amendments", response_model=list[ContractAmendmentRead])
def list_amendments(
    contract_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)
) -> list[ContractAmendmentRead]:
    return contract_controller.list_amendments(db, contract_id, skip, limit)
