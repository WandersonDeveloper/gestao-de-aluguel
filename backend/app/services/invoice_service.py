import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.config import whatsapp
from app.config.settings import settings
from app.domain.exceptions import ConflictError, NotFoundError
from app.domain.invoice_state import assert_valid_transition
from app.models.contract import BillingPeriodicity, Contract
from app.models.contract_item import ContractItem
from app.models.invoice import Invoice, InvoiceStatus
from app.models.message_template import TemplateKey
from app.repositories import (
    client_repository,
    contract_item_repository,
    contract_repository,
    equipment_repository,
    equipment_stock_repository,
    invoice_item_repository,
    invoice_repository,
)
from app.services import message_template_service


def _add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _split_periods(data_inicio: date, data_fim: date, periodicidade: BillingPeriodicity) -> list[date]:
    """Retorna a data de vencimento de cada fatura a ser gerada."""
    if periodicidade == BillingPeriodicity.UNICA:
        return [data_inicio]

    if periodicidade == BillingPeriodicity.DIARIA:
        vencimentos = []
        atual = data_inicio
        while atual <= data_fim:
            vencimentos.append(atual)
            atual += timedelta(days=1)
        return vencimentos

    # MENSAL
    vencimentos = []
    atual = data_inicio
    while atual <= data_fim:
        vencimentos.append(atual)
        atual = _add_months(atual, 1)
    return vencimentos


def _split_valor(valor_total: Decimal, partes: int) -> list[Decimal]:
    """Divide valor_total em N partes de 2 casas decimais, jogando o resto de
    arredondamento na última parte para que a soma bata exatamente com o total."""
    valor_parte = (valor_total / partes).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    valores = [valor_parte] * partes
    diferenca = valor_total - (valor_parte * partes)
    valores[-1] += diferenca
    return valores


def _create_invoice_with_items(
    db: Session, contrato_id: int, data_vencimento: date, valor_fatura: Decimal, itens: list[ContractItem]
) -> Invoice:
    invoice = invoice_repository.create(
        db, {"contrato_id": contrato_id, "data_vencimento": data_vencimento, "valor": valor_fatura}
    )
    valores_item = _split_valor(valor_fatura, len(itens))
    for item, valor_item in zip(itens, valores_item):
        invoice_item_repository.create(
            db, {"invoice_id": invoice.id, "contract_item_id": item.id, "valor": valor_item}
        )
    return invoice


def calcular_valor_item_periodo(
    estoque, quantidade: int, periodicidade: BillingPeriodicity, data_inicio: date, data_fim: date
) -> Decimal | None:
    """Preço de UM item para o período [data_inicio, data_fim], conforme a periodicidade de
    cobrança do contrato — mesmo rateio por período usado em generate_invoices_for_contract
    (ver _split_periods), mas aqui pra saber o valor de um item entrando no meio do contrato
    (ver contract_service.add_items). None quando não há fórmula (HORA é cobrada na baixa,
    UNICA não tem unidade recorrente pra ratear) ou quando o estoque não tem o preço cadastrado."""
    if periodicidade == BillingPeriodicity.DIARIA:
        if estoque.valor_diario is None:
            return None
        dias = len(_split_periods(data_inicio, data_fim, BillingPeriodicity.DIARIA))
        return (estoque.valor_diario * quantidade * dias).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if periodicidade == BillingPeriodicity.MENSAL:
        if estoque.valor_mensal is None:
            return None
        meses = len(_split_periods(data_inicio, data_fim, BillingPeriodicity.MENSAL))
        return (estoque.valor_mensal * quantidade * meses).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return None


def tem_faturas_pendentes(db: Session, contrato_id: int) -> bool:
    """Usado por contract_service.dar_baixa pra impedir baixa total com fatura em aberto —
    força o cliente quitar (ou o admin cancelar a fatura) antes de encerrar o contrato."""
    faturas = invoice_repository.list_by_contrato(db, contrato_id)
    return any(f.status in (InvoiceStatus.PENDENTE, InvoiceStatus.ATRASADA) for f in faturas)


def generate_addendum_invoice(
    db: Session,
    contrato_id: int,
    valor: Decimal,
    itens: list[ContractItem],
    data_vencimento: date | None = None,
) -> Invoice:
    """Fatura avulsa pro valor de um aditivo (ex.: itens adicionados a um
    contrato já ativo — ver contract_service.add_items), sem tocar nas
    faturas já existentes do contrato. Não comita — quem chama controla."""
    return _create_invoice_with_items(db, contrato_id, data_vencimento or date.today(), valor, itens)


def generate_invoices_for_contract(db: Session, contract: Contract) -> list[Invoice]:
    """Não comita a transação — quem chama (contract_service.activate_contract)
    controla o commit, já que essa geração acontece junto com outras mudanças
    (status do contrato, do equipamento) que precisam ser confirmadas atomicamente."""
    if contract.periodicidade_cobranca == BillingPeriodicity.HORA:
        # Cobrança por hora não é conhecida na ativação — a fatura é gerada na
        # baixa, com base nas horas informadas (ver generate_hourly_invoice).
        return []

    itens = contract_item_repository.list_ativos_by_contrato(db, contract.id)
    if not itens:
        return []

    if contract.is_em_aberto:
        # Sem data final conhecida, não há período fechado para ratear —
        # gera só a fatura do primeiro período; as próximas vêm do job diário
        # generate_next_recurring_invoices (ver regras-de-negocio.md).
        if contract.valor_recorrente is None:
            return []
        return [
            _create_invoice_with_items(db, contract.id, contract.data_inicio, contract.valor_recorrente, itens)
        ]

    if contract.valor_total is None:
        return []

    vencimentos = _split_periods(contract.data_inicio, contract.data_fim, contract.periodicidade_cobranca)
    valores_fatura = _split_valor(contract.valor_total, len(vencimentos))

    return [
        _create_invoice_with_items(db, contract.id, data_vencimento, valor_fatura, itens)
        for data_vencimento, valor_fatura in zip(vencimentos, valores_fatura)
    ]


def generate_next_recurring_invoices(db: Session) -> list[Invoice]:
    """Job diário: contratos ativos "em aberto" (sem data final) com
    periodicidade mensal/diária não têm todas as faturas pré-calculadas na
    ativação (não há como, já que não se sabe quando o contrato termina) —
    aqui é onde a próxima fatura de cada período é gerada, assim que o
    período anterior vence. Gera todos os períodos em atraso de uma vez (não
    só o próximo), para não deixar buraco se o job ficar um tempo sem rodar."""
    hoje = date.today()
    contratos = contract_repository.list_ativos_em_aberto_recorrentes(db)
    faturas_geradas: list[Invoice] = []

    for contract in contratos:
        itens = contract_item_repository.list_ativos_by_contrato(db, contract.id)
        if not itens:
            continue

        ultima = invoice_repository.get_ultima_by_contrato(db, contract.id)
        if ultima is None:
            proximo_vencimento = contract.data_inicio
        elif contract.periodicidade_cobranca == BillingPeriodicity.MENSAL:
            proximo_vencimento = _add_months(ultima.data_vencimento, 1)
        else:
            proximo_vencimento = ultima.data_vencimento + timedelta(days=1)

        seguranca = 0
        while proximo_vencimento <= hoje and seguranca < 500:
            faturas_geradas.append(
                _create_invoice_with_items(db, contract.id, proximo_vencimento, contract.valor_recorrente, itens)
            )
            if contract.periodicidade_cobranca == BillingPeriodicity.MENSAL:
                proximo_vencimento = _add_months(proximo_vencimento, 1)
            else:
                proximo_vencimento = proximo_vencimento + timedelta(days=1)
            seguranca += 1

    db.commit()
    for invoice in faturas_geradas:
        db.refresh(invoice)
    return faturas_geradas


def generate_hourly_invoice(
    db: Session, contract: Contract, itens_horas: list[tuple[ContractItem, Decimal]]
) -> Invoice:
    """Gera uma única fatura na baixa de um contrato cobrado por hora
    (periodicidade "hora"), calculando valor = horas × valor_hora do
    equipamento de cada item. Não comita — o commit fica com quem chama
    (contract_service.dar_baixa), pela mesma razão de generate_invoices_for_contract."""
    valores_item: list[tuple[ContractItem, Decimal]] = []
    for item, horas in itens_horas:
        equipamento = equipment_repository.get(db, item.equipamento_id)
        estoque = equipment_stock_repository.get(db, item.equipamento_id, item.filial_id)
        valor_hora = estoque.valor_hora if estoque is not None else None
        if valor_hora is None:
            raise ConflictError(
                f"Equipamento '{equipamento.nome}' não tem valor_hora definido na filial {item.filial_id} — "
                "não é possível calcular a cobrança por hora"
            )
        valor = (horas * valor_hora).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        valores_item.append((item, valor))

    valor_total = sum((valor for _, valor in valores_item), Decimal("0.00"))
    invoice = invoice_repository.create(
        db, {"contrato_id": contract.id, "data_vencimento": date.today(), "valor": valor_total}
    )
    for item, valor in valores_item:
        invoice_item_repository.create(
            db, {"invoice_id": invoice.id, "contract_item_id": item.id, "valor": valor}
        )
    return invoice


def _get_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = invoice_repository.get(db, invoice_id)
    if invoice is None:
        raise NotFoundError(f"Fatura {invoice_id} não encontrada")
    return invoice


def get_invoice(db: Session, invoice_id: int) -> Invoice:
    return _get_invoice(db, invoice_id)


def list_invoices(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    contrato_id: int | None = None,
    status: InvoiceStatus | None = None,
    cliente_id: int | None = None,
) -> list[Invoice]:
    return invoice_repository.list_all(
        db, skip=skip, limit=limit, contrato_id=contrato_id, status=status, cliente_id=cliente_id
    )


def list_invoice_items(db: Session, invoice_id: int):
    _get_invoice(db, invoice_id)
    return invoice_item_repository.list_by_invoice(db, invoice_id)


def cancel_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = _get_invoice(db, invoice_id)
    assert_valid_transition(invoice.status, InvoiceStatus.CANCELADA)
    invoice = invoice_repository.update(db, invoice, {"status": InvoiceStatus.CANCELADA})
    db.commit()
    db.refresh(invoice)
    return invoice


def cancel_invoices_for_contract(db: Session, contrato_id: int) -> None:
    """Cancela faturas ainda em aberto quando o contrato é cancelado (não usado
    em baixa normal — baixa gera cobrança normalmente, cancelamento não)."""
    for invoice in invoice_repository.list_by_contrato(db, contrato_id):
        if invoice.status in (InvoiceStatus.PENDENTE, InvoiceStatus.ATRASADA):
            invoice_repository.update(db, invoice, {"status": InvoiceStatus.CANCELADA})


def mark_overdue_invoices(db: Session) -> list[Invoice]:
    hoje = date.today()
    faturas = invoice_repository.list_pendentes_vencidas(db, hoje)
    for invoice in faturas:
        assert_valid_transition(invoice.status, InvoiceStatus.ATRASADA)
        multa = (invoice.valor * Decimal(str(settings.late_fee_percentage)) / 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        invoice_repository.update(
            db, invoice, {"status": InvoiceStatus.ATRASADA, "multa_juros_aplicado": multa}
        )
    db.commit()
    for invoice in faturas:
        db.refresh(invoice)
    return faturas


def _formatar_valor(valor: Decimal) -> str:
    return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def send_invoice_whatsapp(db: Session, invoice_id: int) -> None:
    invoice = _get_invoice(db, invoice_id)
    contract = contract_repository.get(db, invoice.contrato_id)
    cliente = client_repository.get(db, contract.cliente_id) if contract else None
    if cliente is None or not cliente.telefone:
        raise ConflictError("Cliente não tem telefone cadastrado para envio via WhatsApp")

    vencimento = invoice.data_vencimento.strftime("%d/%m/%Y")
    situacao = "em atraso" if invoice.status == InvoiceStatus.ATRASADA else "pendente"
    multa_texto = ""
    if invoice.status == InvoiceStatus.ATRASADA and invoice.multa_juros_aplicado:
        multa_texto = f" Já foi aplicada uma multa de atraso de {_formatar_valor(invoice.multa_juros_aplicado)}."

    mensagem = message_template_service.render(
        db,
        TemplateKey.COBRANCA_FATURA,
        cliente_nome=cliente.nome,
        situacao=situacao,
        valor=_formatar_valor(invoice.valor),
        vencimento=vencimento,
        multa_texto=multa_texto,
    )
    whatsapp.send_text(cliente.telefone, mensagem)
