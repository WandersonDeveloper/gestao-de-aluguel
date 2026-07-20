from datetime import date as date_type

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.contract_state import assert_valid_transition
from app.domain.equipment_state import assert_valid_transition as assert_valid_equipment_transition
from app.domain.exceptions import ConflictError, InvalidTransitionError, NotFoundError
from app.models.contract import Contract, ContractStatus
from app.models.contract_amendment import ContractAmendmentType
from app.models.contract_item import ContractItem, ContractItemStatus
from app.models.equipment import EquipmentStatus
from app.repositories import (
    client_repository,
    contract_amendment_repository,
    contract_item_repository,
    contract_repository,
    equipment_repository,
)
from app.schemas.contract import ContractCreate
from app.schemas.inventory_movement import EquipmentStatusChange
from app.services import equipment_service, invoice_service


def _get_contract(db: Session, contract_id: int) -> Contract:
    contract = contract_repository.get(db, contract_id)
    if contract is None:
        raise NotFoundError(f"Contrato {contract_id} não encontrado")
    return contract


def create_contract(db: Session, data: ContractCreate) -> Contract:
    if client_repository.get(db, data.cliente_id) is None:
        raise NotFoundError(f"Cliente {data.cliente_id} não encontrado")
    if not data.equipamento_ids:
        raise ConflictError("O contrato precisa de ao menos um equipamento")
    for equipamento_id in data.equipamento_ids:
        if equipment_repository.get(db, equipamento_id) is None:
            raise NotFoundError(f"Equipamento {equipamento_id} não encontrado")

    try:
        contract = contract_repository.create(
            db,
            {
                "cliente_id": data.cliente_id,
                "data_inicio": data.data_inicio,
                "data_fim": data.data_fim,
                "periodicidade_cobranca": data.periodicidade_cobranca,
                "valor_total": data.valor_total,
                "observacoes": data.observacoes,
            },
        )
        for equipamento_id in data.equipamento_ids:
            contract_item_repository.create(
                db,
                {
                    "contrato_id": contract.id,
                    "equipamento_id": equipamento_id,
                    "data_inicio_item": data.data_inicio,
                    "data_fim_item": data.data_fim,
                },
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "Um ou mais equipamentos já possuem reserva conflitante nesse período"
        ) from exc

    db.refresh(contract)
    return contract


def get_contract(db: Session, contract_id: int) -> Contract:
    return _get_contract(db, contract_id)


def list_contracts(
    db: Session, skip: int = 0, limit: int = 50, cliente_id: int | None = None, status=None
) -> list[Contract]:
    return contract_repository.list_all(db, skip=skip, limit=limit, cliente_id=cliente_id, status=status)


def list_items(db: Session, contract_id: int) -> list[ContractItem]:
    _get_contract(db, contract_id)
    return contract_item_repository.list_by_contrato(db, contract_id)


def activate_contract(db: Session, contract_id: int, usuario_id: int) -> Contract:
    contract = _get_contract(db, contract_id)
    assert_valid_transition(contract.status, ContractStatus.ATIVO)

    itens = contract_item_repository.list_ativos_by_contrato(db, contract_id)
    if not itens:
        raise ConflictError("Contrato não possui itens ativos para ativar")

    # Valida todas as transições de equipamento antes de aplicar qualquer uma,
    # para reduzir o risco de ativação parcial caso algum equipamento já esteja ocupado.
    equipamentos = {item.equipamento_id: equipment_repository.get(db, item.equipamento_id) for item in itens}
    for item in itens:
        assert_valid_equipment_transition(equipamentos[item.equipamento_id].status, EquipmentStatus.RESERVADO)

    hoje = date_type.today()
    for item in itens:
        equipamento_id = item.equipamento_id
        equipment_service.change_status(
            db,
            equipamento_id,
            EquipmentStatusChange(status=EquipmentStatus.RESERVADO, motivo=f"Reserva do contrato {contract.id}"),
            usuario_id,
        )
        if item.data_inicio_item <= hoje:
            equipment_service.change_status(
                db,
                equipamento_id,
                EquipmentStatusChange(
                    status=EquipmentStatus.ALUGADO, motivo=f"Início de locação - contrato {contract.id}"
                ),
                usuario_id,
            )

    contract = contract_repository.update(db, contract, {"status": ContractStatus.ATIVO})
    invoice_service.generate_invoices_for_contract(db, contract)
    db.commit()
    db.refresh(contract)
    return contract


def dar_baixa(
    db: Session, contract_id: int, item_ids: list[int] | None, motivo: str | None, usuario_id: int
) -> Contract:
    contract = _get_contract(db, contract_id)
    if contract.status not in (ContractStatus.ATIVO, ContractStatus.VENCIDO):
        raise InvalidTransitionError(
            f"Só é possível dar baixa em contratos ativos ou vencidos (status atual: {contract.status.value})"
        )

    itens_ativos = contract_item_repository.list_ativos_by_contrato(db, contract_id)
    if not itens_ativos:
        raise ConflictError("Contrato não possui itens ativos para dar baixa")

    if item_ids is None:
        itens_para_baixa = itens_ativos
        tipo_amendment = ContractAmendmentType.BAIXA_TOTAL
    else:
        itens_por_id = {item.id: item for item in itens_ativos}
        itens_para_baixa = []
        for item_id in item_ids:
            item = itens_por_id.get(item_id)
            if item is None:
                raise NotFoundError(f"Item de contrato {item_id} não encontrado ou já baixado")
            itens_para_baixa.append(item)
        tipo_amendment = ContractAmendmentType.BAIXA_PARCIAL

    for item in itens_para_baixa:
        equipment_service.change_status(
            db,
            item.equipamento_id,
            EquipmentStatusChange(status=EquipmentStatus.DISPONIVEL, motivo=motivo or "Devolução"),
            usuario_id,
        )
        contract_item_repository.update(db, item, {"status": ContractItemStatus.DEVOLVIDO})

    contract_amendment_repository.create(
        db,
        {
            "contrato_id": contract.id,
            "usuario_id": usuario_id,
            "tipo": tipo_amendment,
            "data_anterior": None,
            "data_nova": None,
            "motivo": motivo,
        },
    )

    itens_restantes = contract_item_repository.list_ativos_by_contrato(db, contract_id)
    if not itens_restantes:
        contract = contract_repository.update(db, contract, {"status": ContractStatus.ENCERRADO})

    db.commit()
    db.refresh(contract)
    return contract


def extend_contract(
    db: Session, contract_id: int, nova_data_fim: date_type, motivo: str | None, usuario_id: int
) -> Contract:
    contract = _get_contract(db, contract_id)
    if contract.status not in (ContractStatus.ATIVO, ContractStatus.VENCIDO):
        raise InvalidTransitionError(
            f"Só é possível estender contratos ativos ou vencidos (status atual: {contract.status.value})"
        )
    if nova_data_fim <= contract.data_fim:
        raise ConflictError("A nova data final deve ser posterior à data final atual do contrato")

    data_anterior = contract.data_fim
    itens_ativos = contract_item_repository.list_ativos_by_contrato(db, contract_id)

    try:
        for item in itens_ativos:
            contract_item_repository.update(db, item, {"data_fim_item": nova_data_fim})
        novo_status = ContractStatus.ATIVO if nova_data_fim >= date_type.today() else contract.status
        contract = contract_repository.update(db, contract, {"data_fim": nova_data_fim, "status": novo_status})
        contract_amendment_repository.create(
            db,
            {
                "contrato_id": contract.id,
                "usuario_id": usuario_id,
                "tipo": ContractAmendmentType.EXTENSAO,
                "data_anterior": data_anterior,
                "data_nova": nova_data_fim,
                "motivo": motivo,
            },
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "A nova data conflita com outra reserva existente para algum equipamento do contrato"
        ) from exc

    db.refresh(contract)
    return contract


def cancel_contract(db: Session, contract_id: int, motivo: str | None, usuario_id: int) -> Contract:
    contract = _get_contract(db, contract_id)
    assert_valid_transition(contract.status, ContractStatus.CANCELADO)

    status_original = contract.status
    itens_ativos = contract_item_repository.list_ativos_by_contrato(db, contract_id)
    for item in itens_ativos:
        if status_original in (ContractStatus.ATIVO, ContractStatus.VENCIDO):
            equipment_service.change_status(
                db,
                item.equipamento_id,
                EquipmentStatusChange(status=EquipmentStatus.DISPONIVEL, motivo=motivo or "Cancelamento do contrato"),
                usuario_id,
            )
        contract_item_repository.update(db, item, {"status": ContractItemStatus.DEVOLVIDO})

    contract = contract_repository.update(db, contract, {"status": ContractStatus.CANCELADO})
    contract_amendment_repository.create(
        db,
        {
            "contrato_id": contract.id,
            "usuario_id": usuario_id,
            "tipo": ContractAmendmentType.CANCELAMENTO,
            "data_anterior": None,
            "data_nova": None,
            "motivo": motivo,
        },
    )
    invoice_service.cancel_invoices_for_contract(db, contract.id)
    db.commit()
    db.refresh(contract)
    return contract


def list_amendments(db: Session, contract_id: int, skip: int = 0, limit: int = 50):
    _get_contract(db, contract_id)
    return contract_amendment_repository.list_by_contrato(db, contract_id, skip=skip, limit=limit)


def mark_expired_contracts(db: Session) -> list[Contract]:
    # Job diário (seção 4.2 do plano): contratos ativos cuja data_fim já passou
    # migram para "vencido". É uma transição automática de rotina, sem usuário
    # responsável, por isso não gera registro em contract_amendments (que é
    # reservado para decisões de negócio: extensão, baixa, cancelamento).
    hoje = date_type.today()
    contratos = contract_repository.list_expirable(db, hoje)
    for contract in contratos:
        assert_valid_transition(contract.status, ContractStatus.VENCIDO)
        contract_repository.update(db, contract, {"status": ContractStatus.VENCIDO})
    db.commit()
    for contract in contratos:
        db.refresh(contract)
    return contratos
