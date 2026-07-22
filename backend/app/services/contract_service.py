from datetime import date as date_type
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.contract_state import assert_valid_transition
from app.domain.equipment_state import assert_valid_transition as assert_valid_equipment_transition
from app.domain.exceptions import ConflictError, InvalidTransitionError, NotFoundError
from app.models.contract import OPEN_ENDED_SENTINEL_DATE, BillingPeriodicity, Contract, ContractStatus
from app.models.contract_amendment import ContractAmendmentType
from app.models.contract_item import ContractItem, ContractItemStatus
from app.models.equipment import EquipmentStatus
from app.models.equipment_stock import EquipmentStock
from app.repositories import (
    client_repository,
    contract_amendment_repository,
    contract_item_repository,
    contract_repository,
    equipment_repository,
    equipment_stock_repository,
)
from app.schemas.contract import ContractCreate, ContractItemRequest
from app.schemas.inventory_movement import EquipmentStatusChange
from app.services import contract_signature_service, equipment_service, invoice_service


def _get_contract(db: Session, contract_id: int) -> Contract:
    contract = contract_repository.get(db, contract_id)
    if contract is None:
        raise NotFoundError(f"Contrato {contract_id} não encontrado")
    return contract


def _checar_disponibilidade(
    db: Session,
    estoque: EquipmentStock,
    quantidade: int,
    data_inicio: date_type,
    data_fim: date_type,
    excluir_item_id: int | None = None,
) -> None:
    reservado = contract_item_repository.sum_quantidade_ativa_overlap(
        db, estoque.equipamento_id, estoque.filial_id, data_inicio, data_fim, excluir_item_id=excluir_item_id
    )
    if reservado + quantidade > estoque.quantidade:
        disponivel = max(estoque.quantidade - reservado, 0)
        raise ConflictError(
            f"Equipamento não possui estoque suficiente na filial {estoque.filial_id} no período "
            f"(disponível: {disponivel}, solicitado: {quantidade})"
        )


def create_contract(db: Session, data: ContractCreate) -> Contract:
    if client_repository.get(db, data.cliente_id) is None:
        raise NotFoundError(f"Cliente {data.cliente_id} não encontrado")
    if not data.itens:
        raise ConflictError("O contrato precisa de ao menos um equipamento")

    # data_fim None = contrato "em aberto" (sem término definido). Cobrança
    # "única" pressupõe um período conhecido para ratear o valor_total, então
    # não faz sentido sem data final — ver regras-de-negocio.md.
    if data.data_fim is None and data.periodicidade_cobranca == BillingPeriodicity.UNICA:
        raise ConflictError(
            "Contrato em aberto (sem data final) não pode ter periodicidade de cobrança única — "
            "use mensal, diária ou hora"
        )
    data_fim_efetivo = data.data_fim if data.data_fim is not None else OPEN_ENDED_SENTINEL_DATE

    # Trava cada par (equipamento, filial) (SELECT ... FOR UPDATE) antes de checar
    # a soma de quantidade já reservada no período, para evitar overbooking em
    # requisições concorrentes — substitui a antiga EXCLUDE constraint do
    # Postgres, que garantia exclusividade de data mas não suportava reserva
    # parcial de estoque nem estoque dividido por filial.
    for item_request in data.itens:
        estoque = equipment_stock_repository.get_for_update(
            db, item_request.equipamento_id, item_request.filial_id
        )
        if estoque is None:
            raise NotFoundError(
                f"Equipamento {item_request.equipamento_id} não tem estoque cadastrado "
                f"na filial {item_request.filial_id}"
            )
        _checar_disponibilidade(db, estoque, item_request.quantidade, data.data_inicio, data_fim_efetivo)

    contract = contract_repository.create(
        db,
        {
            "cliente_id": data.cliente_id,
            "data_inicio": data.data_inicio,
            "data_fim": data_fim_efetivo,
            "tipo": data.tipo,
            "periodicidade_cobranca": data.periodicidade_cobranca,
            "valor_total": data.valor_total,
            "valor_recorrente": data.valor_recorrente,
            "observacoes": data.observacoes,
        },
    )
    for item_request in data.itens:
        contract_item_repository.create(
            db,
            {
                "contrato_id": contract.id,
                "equipamento_id": item_request.equipamento_id,
                "filial_id": item_request.filial_id,
                "quantidade": item_request.quantidade,
                "data_inicio_item": data.data_inicio,
                "data_fim_item": data_fim_efetivo,
            },
        )
    db.commit()
    db.refresh(contract)
    return contract


def get_contract(db: Session, contract_id: int) -> Contract:
    return _get_contract(db, contract_id)


def list_contracts(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    cliente_id: int | None = None,
    status=None,
    tipo=None,
    assinatura_status=None,
) -> list[Contract]:
    return contract_repository.list_all(
        db, skip=skip, limit=limit, cliente_id=cliente_id, status=status, tipo=tipo, assinatura_status=assinatura_status
    )


def list_items(db: Session, contract_id: int) -> list[ContractItem]:
    _get_contract(db, contract_id)
    return contract_item_repository.list_by_contrato(db, contract_id)


def activate_contract(db: Session, contract_id: int, usuario_id: int) -> Contract:
    contract = _get_contract(db, contract_id)
    assert_valid_transition(contract.status, ContractStatus.ATIVO)

    itens = contract_item_repository.list_ativos_by_contrato(db, contract_id)
    if not itens:
        raise ConflictError("Contrato não possui itens ativos para ativar")

    # Itens de estoque (quantidade_total > 1, ou espalhados por várias filiais)
    # não passam pela máquina de estado de equipamento — ela só faz sentido
    # para equipamentos serializados (uma única filial, quantidade 1).
    equipamentos = {item.equipamento_id: equipment_repository.get(db, item.equipamento_id) for item in itens}
    for item in itens:
        equipamento = equipamentos[item.equipamento_id]
        if not equipamento.is_estoque:
            assert_valid_equipment_transition(equipamento.status, EquipmentStatus.RESERVADO)

    hoje = date_type.today()
    for item in itens:
        equipamento = equipamentos[item.equipamento_id]
        if equipamento.is_estoque:
            continue
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
    db: Session,
    contract_id: int,
    item_ids: list[int] | None,
    motivo: str | None,
    usuario_id: int,
    horas_por_item: dict[int, Decimal] | None = None,
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
        if invoice_service.tem_faturas_pendentes(db, contract_id):
            raise ConflictError(
                "Não é possível encerrar o contrato com faturas pendentes ou atrasadas — "
                "quite ou cancele as faturas em aberto antes de dar baixa total"
            )
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

    is_cobranca_por_hora = contract.periodicidade_cobranca == BillingPeriodicity.HORA
    itens_horas: list[tuple[ContractItem, Decimal]] = []
    if is_cobranca_por_hora:
        horas_por_item = horas_por_item or {}
        for item in itens_para_baixa:
            horas = horas_por_item.get(item.id)
            if horas is None:
                raise ConflictError(
                    f"Informe as horas trabalhadas do item {item.id} — contrato é cobrado por hora"
                )
            if horas <= 0:
                raise ConflictError(f"As horas trabalhadas do item {item.id} devem ser positivas")
            itens_horas.append((item, horas))

    for item in itens_para_baixa:
        equipamento = equipment_repository.get(db, item.equipamento_id)
        if not equipamento.is_estoque:
            equipment_service.change_status(
                db,
                item.equipamento_id,
                EquipmentStatusChange(status=EquipmentStatus.DISPONIVEL, motivo=motivo or "Devolução"),
                usuario_id,
            )
        updates = {"status": ContractItemStatus.DEVOLVIDO}
        if is_cobranca_por_hora:
            updates["horas_trabalhadas"] = next(h for i, h in itens_horas if i.id == item.id)
        contract_item_repository.update(db, item, updates)

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

    if is_cobranca_por_hora:
        invoice_service.generate_hourly_invoice(db, contract, itens_horas)

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
    if contract.is_em_aberto:
        raise ConflictError("Contrato em aberto não tem data final — não há o que estender")
    if nova_data_fim <= contract.data_fim:
        raise ConflictError("A nova data final deve ser posterior à data final atual do contrato")

    data_anterior = contract.data_fim
    itens_ativos = contract_item_repository.list_ativos_by_contrato(db, contract_id)

    # Sem a EXCLUDE constraint, a checagem de conflito de datas precisa ser
    # feita explicitamente aqui, travando cada par (equipamento, filial) e
    # comparando a soma de quantidade já reservada no novo período contra o
    # estoque daquela filial.
    for item in itens_ativos:
        estoque = equipment_stock_repository.get_for_update(db, item.equipamento_id, item.filial_id)
        _checar_disponibilidade(
            db, estoque, item.quantidade, item.data_inicio_item, nova_data_fim, excluir_item_id=item.id
        )

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
    db.refresh(contract)
    return contract


def add_items(
    db: Session,
    contract_id: int,
    itens: list[ContractItemRequest],
    condicao_cobranca_item: BillingPeriodicity | None,
    motivo: str | None,
    usuario_id: int,
    data_vencimento_aditivo: date_type | None = None,
) -> Contract:
    """Adiciona equipamento a um contrato já ativo (aditivo) sem precisar
    criar um contrato novo — ex.: cliente pede mais andaimes no meio do
    prazo. O valor do aditivo é SEMPRE calculado a partir do preço cadastrado
    no estoque do equipamento (valor_diario/valor_mensal), nunca digitado
    manualmente — ver invoice_service.calcular_valor_item_periodo. Contratos
    "diária"/"mensal" usam a própria periodicidade do contrato; contratos de
    cobrança "única" não têm taxa recorrente própria, então `condicao_cobranca_item`
    (diária ou mensal) precisa ser informado pra saber qual preço usar.
    Cobrança por hora não gera fatura agora — é cobrada na baixa, junto com o
    resto do contrato."""
    contract = _get_contract(db, contract_id)
    if contract.status != ContractStatus.ATIVO:
        raise InvalidTransitionError(
            f"Só é possível adicionar item a contratos ativos (status atual: {contract.status.value}) — "
            "se o contrato estiver vencido, estenda o prazo primeiro"
        )
    if not itens:
        raise ConflictError("Informe ao menos um equipamento para adicionar")

    if contract.periodicidade_cobranca in (BillingPeriodicity.DIARIA, BillingPeriodicity.MENSAL):
        condicao = contract.periodicidade_cobranca
    elif contract.periodicidade_cobranca == BillingPeriodicity.HORA:
        condicao = None  # cobrada na baixa, nunca gera fatura avulsa aqui
    else:  # UNICA — sem taxa recorrente própria, precisa que o admin escolha
        # qual condição usar pra cobrar o item; sem escolher, adiciona sem cobrança
        # (equivalente a considerar o item já coberto pelo valor fechado do contrato).
        if condicao_cobranca_item is not None and condicao_cobranca_item not in (
            BillingPeriodicity.DIARIA,
            BillingPeriodicity.MENSAL,
        ):
            raise ConflictError(
                "condicao_cobranca_item só pode ser diária ou mensal — cobrança por hora não é "
                "suportada em contratos de cobrança única (não há baixa automática por hora)"
            )
        condicao = condicao_cobranca_item

    hoje = date_type.today()

    amendment = contract_amendment_repository.create(
        db,
        {
            "contrato_id": contract.id,
            "usuario_id": usuario_id,
            "tipo": ContractAmendmentType.ADICAO_ITEM,
            "data_anterior": hoje,
            "data_nova": contract.data_fim,
            "motivo": motivo,
        },
    )

    novos_itens: list[ContractItem] = []
    valor_calculado = Decimal("0.00")
    for item_request in itens:
        estoque = equipment_stock_repository.get_for_update(
            db, item_request.equipamento_id, item_request.filial_id
        )
        if estoque is None:
            raise NotFoundError(
                f"Equipamento {item_request.equipamento_id} não tem estoque cadastrado "
                f"na filial {item_request.filial_id}"
            )
        _checar_disponibilidade(db, estoque, item_request.quantidade, hoje, contract.data_fim)
        item = contract_item_repository.create(
            db,
            {
                "contrato_id": contract.id,
                "equipamento_id": item_request.equipamento_id,
                "filial_id": item_request.filial_id,
                "quantidade": item_request.quantidade,
                "data_inicio_item": hoje,
                "data_fim_item": contract.data_fim,
                "amendment_id": amendment.id,
            },
        )
        novos_itens.append(item)

        if condicao is not None:
            valor_item = invoice_service.calcular_valor_item_periodo(
                estoque, item_request.quantidade, condicao, hoje, contract.data_fim
            )
            if valor_item is None:
                raise ConflictError(
                    f"Equipamento {item_request.equipamento_id} não tem "
                    f"{'valor_diario' if condicao == BillingPeriodicity.DIARIA else 'valor_mensal'} "
                    f"cadastrado na filial {item_request.filial_id} — cadastre o preço antes de adicionar ao contrato"
                )
            valor_calculado += valor_item

    valor_aditivo = valor_calculado if condicao is not None else None

    if valor_aditivo is not None:
        invoice_service.generate_addendum_invoice(
            db, contract.id, valor_aditivo, novos_itens, data_vencimento=data_vencimento_aditivo
        )
        # Contabiliza o aditivo no total do contrato — só quando o contrato já
        # tinha valor_total (contrato de prazo fixo); contratos em aberto usam
        # valor_recorrente, que não faz sentido somar aqui (é por período, não total).
        if contract.valor_total is not None:
            contract = contract_repository.update(
                db, contract, {"valor_total": contract.valor_total + valor_aditivo}
            )

    contract_signature_service.enviar_confirmacao_aditivo(db, amendment, contract, novos_itens, valor_aditivo)

    db.commit()
    db.refresh(contract)
    return contract


def cancel_contract(db: Session, contract_id: int, motivo: str | None, usuario_id: int) -> Contract:
    contract = _get_contract(db, contract_id)
    assert_valid_transition(contract.status, ContractStatus.CANCELADO)

    status_original = contract.status
    itens_ativos = contract_item_repository.list_ativos_by_contrato(db, contract_id)
    for item in itens_ativos:
        equipamento = equipment_repository.get(db, item.equipamento_id)
        if status_original in (ContractStatus.ATIVO, ContractStatus.VENCIDO) and not equipamento.is_estoque:
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


def delete_contract(db: Session, contract_id: int) -> None:
    contract = _get_contract(db, contract_id)
    # Só permite apagar contratos em rascunho, que nunca foram ativados: um
    # contrato ativado gera fatura, movimenta estoque e cria histórico
    # (amendments) que precisam ser preservados para auditoria — para esses
    # casos, a via correta é cancelar (POST /cancel), não apagar.
    if contract.status != ContractStatus.RASCUNHO:
        raise ConflictError(
            "Só é possível excluir contratos em rascunho — contratos já ativados têm "
            "histórico financeiro/operacional que precisa ser preservado. Use cancelar."
        )
    contract_item_repository.delete_by_contrato(db, contract_id)
    contract_repository.delete(db, contract)


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
