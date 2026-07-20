import calendar
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.domain.exceptions import NotFoundError
from app.domain.invoice_state import assert_valid_transition
from app.models.contract import BillingPeriodicity, Contract
from app.models.invoice import Invoice, InvoiceStatus
from app.repositories import contract_item_repository, invoice_item_repository, invoice_repository


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


def generate_invoices_for_contract(db: Session, contract: Contract) -> list[Invoice]:
    """Não comita a transação — quem chama (contract_service.activate_contract)
    controla o commit, já que essa geração acontece junto com outras mudanças
    (status do contrato, do equipamento) que precisam ser confirmadas atomicamente."""
    if contract.valor_total is None:
        return []

    itens = contract_item_repository.list_ativos_by_contrato(db, contract.id)
    if not itens:
        return []

    vencimentos = _split_periods(contract.data_inicio, contract.data_fim, contract.periodicidade_cobranca)
    valores_fatura = _split_valor(contract.valor_total, len(vencimentos))

    invoices = []
    for data_vencimento, valor_fatura in zip(vencimentos, valores_fatura):
        invoice = invoice_repository.create(
            db, {"contrato_id": contract.id, "data_vencimento": data_vencimento, "valor": valor_fatura}
        )
        valores_item = _split_valor(valor_fatura, len(itens))
        for item, valor_item in zip(itens, valores_item):
            invoice_item_repository.create(
                db, {"invoice_id": invoice.id, "contract_item_id": item.id, "valor": valor_item}
            )
        invoices.append(invoice)

    return invoices


def _get_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = invoice_repository.get(db, invoice_id)
    if invoice is None:
        raise NotFoundError(f"Fatura {invoice_id} não encontrada")
    return invoice


def get_invoice(db: Session, invoice_id: int) -> Invoice:
    return _get_invoice(db, invoice_id)


def list_invoices(
    db: Session, skip: int = 0, limit: int = 50, contrato_id: int | None = None, status: InvoiceStatus | None = None
) -> list[Invoice]:
    return invoice_repository.list_all(db, skip=skip, limit=limit, contrato_id=contrato_id, status=status)


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
