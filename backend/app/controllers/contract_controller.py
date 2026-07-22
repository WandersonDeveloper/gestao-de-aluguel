from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.contract import BillingPeriodicity, Contract, ContractSignatureStatus, ContractStatus, ContractType
from app.models.contract_amendment import ContractAmendment
from app.models.contract_item import ContractItem
from app.schemas.contract import ContractCreate, ContractItemRequest
from app.services import contract_document_service, contract_service, contract_signature_service


def create_contract(db: Session, data: ContractCreate) -> Contract:
    return contract_service.create_contract(db, data)


def get_contract(db: Session, contract_id: int) -> Contract:
    return contract_service.get_contract(db, contract_id)


def list_contracts(
    db: Session,
    skip: int,
    limit: int,
    cliente_id: int | None,
    status: ContractStatus | None,
    tipo: ContractType | None = None,
    assinatura_status: ContractSignatureStatus | None = None,
) -> list[Contract]:
    return contract_service.list_contracts(
        db, skip=skip, limit=limit, cliente_id=cliente_id, status=status, tipo=tipo, assinatura_status=assinatura_status
    )


def list_items(db: Session, contract_id: int) -> list[ContractItem]:
    return contract_service.list_items(db, contract_id)


def activate_contract(db: Session, contract_id: int, usuario_id: int) -> Contract:
    return contract_service.activate_contract(db, contract_id, usuario_id)


def dar_baixa(
    db: Session,
    contract_id: int,
    item_ids: list[int] | None,
    motivo: str | None,
    usuario_id: int,
    horas_por_item: dict[int, Decimal] | None = None,
) -> Contract:
    return contract_service.dar_baixa(db, contract_id, item_ids, motivo, usuario_id, horas_por_item)


def extend_contract(db: Session, contract_id: int, nova_data_fim, motivo: str | None, usuario_id: int) -> Contract:
    return contract_service.extend_contract(db, contract_id, nova_data_fim, motivo, usuario_id)


def add_items(
    db: Session,
    contract_id: int,
    itens: list[ContractItemRequest],
    condicao_cobranca_item: BillingPeriodicity | None,
    motivo: str | None,
    usuario_id: int,
    data_vencimento_aditivo: date | None = None,
) -> Contract:
    return contract_service.add_items(
        db, contract_id, itens, condicao_cobranca_item, motivo, usuario_id, data_vencimento_aditivo
    )


def cancel_contract(db: Session, contract_id: int, motivo: str | None, usuario_id: int) -> Contract:
    return contract_service.cancel_contract(db, contract_id, motivo, usuario_id)


def list_amendments(db: Session, contract_id: int, skip: int, limit: int) -> list[ContractAmendment]:
    return contract_service.list_amendments(db, contract_id, skip=skip, limit=limit)


def generate_document(db: Session, contract_id: int) -> bytes:
    return contract_document_service.generate_contract_pdf(db, contract_id)


def send_whatsapp(db: Session, contract_id: int) -> None:
    contract_document_service.send_contract_whatsapp(db, contract_id)


def get_comprovante_assinatura(db: Session, contract_id: int) -> bytes:
    return contract_signature_service.get_comprovante_pdf(db, contract_id)


def get_comprovante_aditivo(db: Session, contract_id: int, amendment_id: int) -> bytes:
    return contract_signature_service.get_comprovante_aditivo_pdf(db, contract_id, amendment_id)


def delete_contract(db: Session, contract_id: int) -> None:
    contract_service.delete_contract(db, contract_id)
