from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.contract import Contract, ContractStatus
from app.models.contract_item import ContractItem
from app.models.equipment import Equipment, EquipmentStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.payment import Payment
from app.models.service_order import ServiceOrder, ServiceOrderStatus
from app.schemas.report import (
    DashboardReport,
    MostRentedEquipmentEntry,
    OverdueByClientEntry,
    OverdueInvoiceEntry,
    RentalReport,
)


def rental_report(db: Session, data_inicio: date | None, data_fim: date | None) -> RentalReport:
    stmt = select(Contract)
    if data_inicio is not None:
        stmt = stmt.where(Contract.data_inicio >= data_inicio)
    if data_fim is not None:
        stmt = stmt.where(Contract.data_inicio <= data_fim)
    contratos = list(db.scalars(stmt))

    def _count(status: ContractStatus) -> int:
        return sum(1 for c in contratos if c.status == status)

    return RentalReport(
        total_contratos=len(contratos),
        contratos_rascunho=_count(ContractStatus.RASCUNHO),
        contratos_ativos=_count(ContractStatus.ATIVO),
        contratos_vencidos=_count(ContractStatus.VENCIDO),
        contratos_encerrados=_count(ContractStatus.ENCERRADO),
        contratos_cancelados=_count(ContractStatus.CANCELADO),
        valor_total_contratado=sum((c.valor_total or Decimal("0") for c in contratos), Decimal("0")),
    )


def most_rented_equipment(db: Session, limit: int = 10) -> list[MostRentedEquipmentEntry]:
    stmt = (
        select(Equipment.id, Equipment.nome, func.count(ContractItem.id).label("quantidade"))
        .join(ContractItem, ContractItem.equipamento_id == Equipment.id)
        .group_by(Equipment.id, Equipment.nome)
        .order_by(func.count(ContractItem.id).desc())
        .limit(limit)
    )
    return [
        MostRentedEquipmentEntry(equipamento_id=row.id, equipamento_nome=row.nome, quantidade_locacoes=row.quantidade)
        for row in db.execute(stmt)
    ]


def overdue_report(db: Session) -> list[OverdueByClientEntry]:
    stmt = (
        select(Invoice, Contract, Client)
        .join(Contract, Contract.id == Invoice.contrato_id)
        .join(Client, Client.id == Contract.cliente_id)
        .where(Invoice.status == InvoiceStatus.ATRASADA)
        .order_by(Client.nome, Invoice.data_vencimento)
    )

    por_cliente: dict[int, OverdueByClientEntry] = {}
    for invoice, contract, client in db.execute(stmt):
        entry = por_cliente.get(client.id)
        if entry is None:
            entry = OverdueByClientEntry(
                cliente_id=client.id,
                cliente_nome=client.nome,
                quantidade_faturas=0,
                total_atrasado=Decimal("0"),
                faturas=[],
            )
            por_cliente[client.id] = entry
        entry.quantidade_faturas += 1
        entry.total_atrasado += invoice.valor
        entry.faturas.append(
            OverdueInvoiceEntry(
                invoice_id=invoice.id,
                contrato_id=contract.id,
                data_vencimento=invoice.data_vencimento.isoformat(),
                valor=invoice.valor,
                multa_juros_aplicado=invoice.multa_juros_aplicado,
            )
        )
    return list(por_cliente.values())


def dashboard_report(db: Session) -> DashboardReport:
    def _count_equipment(status: EquipmentStatus) -> int:
        stmt = select(func.count()).select_from(Equipment).where(Equipment.status == status)
        return db.scalar(stmt) or 0

    def _count_contracts(status: ContractStatus) -> int:
        stmt = select(func.count()).select_from(Contract).where(Contract.status == status)
        return db.scalar(stmt) or 0

    equipamentos_total = db.scalar(select(func.count()).select_from(Equipment)) or 0

    ordens_abertas = (
        db.scalar(
            select(func.count())
            .select_from(ServiceOrder)
            .where(ServiceOrder.status.in_((ServiceOrderStatus.ABERTA, ServiceOrderStatus.EM_ANDAMENTO)))
        )
        or 0
    )

    faturas_atrasadas = list(db.scalars(select(Invoice).where(Invoice.status == InvoiceStatus.ATRASADA)))

    hoje = date.today()
    inicio_mes = hoje.replace(day=1)
    receita_mes = db.scalar(
        select(func.coalesce(func.sum(Payment.valor), 0)).where(func.date(Payment.created_at) >= inicio_mes)
    ) or Decimal("0")

    return DashboardReport(
        equipamentos_total=equipamentos_total,
        equipamentos_disponiveis=_count_equipment(EquipmentStatus.DISPONIVEL),
        equipamentos_reservados=_count_equipment(EquipmentStatus.RESERVADO),
        equipamentos_alugados=_count_equipment(EquipmentStatus.ALUGADO),
        equipamentos_manutencao=_count_equipment(EquipmentStatus.MANUTENCAO),
        contratos_ativos=_count_contracts(ContractStatus.ATIVO),
        contratos_vencidos=_count_contracts(ContractStatus.VENCIDO),
        ordens_servico_abertas=ordens_abertas,
        faturas_atrasadas_quantidade=len(faturas_atrasadas),
        faturas_atrasadas_valor_total=sum((f.valor for f in faturas_atrasadas), Decimal("0")),
        receita_recebida_mes_atual=receita_mes,
    )
