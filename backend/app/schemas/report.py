from decimal import Decimal

from pydantic import BaseModel


class RentalReport(BaseModel):
    total_contratos: int
    contratos_rascunho: int
    contratos_ativos: int
    contratos_vencidos: int
    contratos_encerrados: int
    contratos_cancelados: int
    valor_total_contratado: Decimal


class MostRentedEquipmentEntry(BaseModel):
    equipamento_id: int
    equipamento_nome: str
    quantidade_locacoes: int


class OverdueInvoiceEntry(BaseModel):
    invoice_id: int
    contrato_id: int
    data_vencimento: str
    valor: Decimal
    multa_juros_aplicado: Decimal | None


class OverdueByClientEntry(BaseModel):
    cliente_id: int
    cliente_nome: str
    quantidade_faturas: int
    total_atrasado: Decimal
    faturas: list[OverdueInvoiceEntry]


class DashboardReport(BaseModel):
    equipamentos_total: int
    equipamentos_disponiveis: int
    equipamentos_reservados: int
    equipamentos_alugados: int
    equipamentos_manutencao: int
    contratos_ativos: int
    contratos_vencidos: int
    ordens_servico_abertas: int
    faturas_atrasadas_quantidade: int
    faturas_atrasadas_valor_total: Decimal
    receita_recebida_mes_atual: Decimal
