from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import contract_controller
from app.models.contract import ContractSignatureStatus, ContractStatus, ContractType
from app.models.user import User, UserRole
from app.schemas.contract import (
    ContractAddItemsRequest,
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
    tipo: ContractType | None = None,
    assinatura_status: ContractSignatureStatus | None = None,
    db: Session = Depends(get_db),
) -> list[ContractRead]:
    return contract_controller.list_contracts(db, skip, limit, cliente_id, status, tipo, assinatura_status)


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
    return contract_controller.dar_baixa(
        db, contract_id, data.item_ids, data.motivo, current_user.id, data.horas_por_item
    )


@router.post("/{contract_id}/extend", response_model=ContractRead)
def extend_contract(
    contract_id: int,
    data: ContractExtendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ContractRead:
    return contract_controller.extend_contract(db, contract_id, data.nova_data_fim, data.motivo, current_user.id)


@router.post("/{contract_id}/add-items", response_model=ContractRead)
def add_items(
    contract_id: int,
    data: ContractAddItemsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> ContractRead:
    return contract_controller.add_items(
        db,
        contract_id,
        data.itens,
        data.condicao_cobranca_item,
        data.motivo,
        current_user.id,
        data.data_vencimento_aditivo,
    )


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


@router.get("/{contract_id}/documento")
def generate_document(contract_id: int, db: Session = Depends(get_db)) -> Response:
    pdf_bytes = contract_controller.generate_document(db, contract_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="contrato_{contract_id}.pdf"'},
    )


@router.post("/{contract_id}/send-whatsapp", status_code=status.HTTP_204_NO_CONTENT)
def send_contract_whatsapp(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN, UserRole.OPERADOR)),
) -> None:
    contract_controller.send_whatsapp(db, contract_id)


@router.get("/{contract_id}/comprovante-assinatura")
def get_comprovante_assinatura(contract_id: int, db: Session = Depends(get_db)) -> Response:
    pdf_bytes = contract_controller.get_comprovante_assinatura(db, contract_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="comprovante_aceite_contrato_{contract_id}.pdf"'},
    )


@router.get("/{contract_id}/amendments/{amendment_id}/comprovante-assinatura")
def get_comprovante_aditivo(contract_id: int, amendment_id: int, db: Session = Depends(get_db)) -> Response:
    pdf_bytes = contract_controller.get_comprovante_aditivo(db, contract_id, amendment_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="comprovante_aceite_aditivo_{amendment_id}.pdf"'
        },
    )


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> None:
    contract_controller.delete_contract(db, contract_id)
