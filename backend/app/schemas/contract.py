from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.contract import BillingPeriodicity, ContractStatus
from app.models.contract_item import ContractItemStatus


class ContractItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contrato_id: int
    equipamento_id: int
    data_inicio_item: date
    data_fim_item: date
    status: ContractItemStatus
    valor_item: Decimal | None


class ContractCreate(BaseModel):
    cliente_id: int
    data_inicio: date
    data_fim: date
    equipamento_ids: list[int]
    periodicidade_cobranca: BillingPeriodicity = BillingPeriodicity.UNICA
    valor_total: Decimal | None = None
    observacoes: str | None = None


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    data_inicio: date
    data_fim: date
    status: ContractStatus
    periodicidade_cobranca: BillingPeriodicity
    valor_total: Decimal | None
    observacoes: str | None
    created_at: datetime


class ContractWithItemsRead(ContractRead):
    itens: list[ContractItemRead]


class ContractBaixaRequest(BaseModel):
    item_ids: list[int] | None = None  # None = baixa total (todos os itens ativos)
    motivo: str | None = None


class ContractExtendRequest(BaseModel):
    nova_data_fim: date
    motivo: str | None = None


class ContractCancelRequest(BaseModel):
    motivo: str | None = None
