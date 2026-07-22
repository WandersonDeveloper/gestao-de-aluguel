from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.contract import (
    OPEN_ENDED_SENTINEL_DATE,
    BillingPeriodicity,
    ContractSignatureStatus,
    ContractStatus,
    ContractType,
)
from app.models.contract_item import ContractItemStatus


def _none_se_sentinela(valor: date) -> date | None:
    return None if valor >= OPEN_ENDED_SENTINEL_DATE else valor


class ContractItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contrato_id: int
    equipamento_id: int
    filial_id: int
    data_inicio_item: date
    data_fim_item: date
    quantidade: int
    status: ContractItemStatus
    valor_item: Decimal | None
    horas_trabalhadas: Decimal | None

    @field_serializer("data_fim_item")
    def _serialize_data_fim_item(self, valor: date) -> date | None:
        return _none_se_sentinela(valor)


class ContractItemRequest(BaseModel):
    equipamento_id: int
    filial_id: int
    quantidade: int = Field(default=1, ge=1)


class ContractCreate(BaseModel):
    cliente_id: int
    data_inicio: date
    # None = contrato "em aberto", sem data de término definida — ver
    # regras-de-negocio.md sobre a data-sentinela usada internamente e as
    # restrições (periodicidade não pode ser "unica", extend não se aplica).
    data_fim: date | None = None
    itens: list[ContractItemRequest]
    tipo: ContractType = ContractType.LOCACAO
    periodicidade_cobranca: BillingPeriodicity = BillingPeriodicity.UNICA
    valor_total: Decimal | None = None
    # Valor cobrado a cada período, usado só quando data_fim é None (contrato
    # em aberto) — ver invoice_service.generate_next_recurring_invoices.
    valor_recorrente: Decimal | None = None
    observacoes: str | None = None

    @field_validator("valor_total", "valor_recorrente", mode="before")
    @classmethod
    def _string_vazia_vira_none(cls, valor):
        # Campos numéricos opcionais vindos de formulário HTML chegam como ""
        # quando o usuário deixa em branco, não como null/ausente — Decimal
        # não aceita string vazia, então normalizamos aqui antes da validação.
        if isinstance(valor, str) and valor.strip() == "":
            return None
        return valor


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cliente_id: int
    data_inicio: date
    # date | None (não só `date`): embora a serialização já transforme a
    # data-sentinela em None, essa rota reconstrói ContractWithItemsRead a
    # partir de um dict já serializado (model_validate(...).model_dump()) —
    # sem esse tipo aceitar None, a revalidação desse dict falharia.
    data_fim: date | None
    status: ContractStatus
    tipo: ContractType
    periodicidade_cobranca: BillingPeriodicity
    valor_total: Decimal | None
    valor_recorrente: Decimal | None
    observacoes: str | None
    assinatura_status: ContractSignatureStatus
    assinatura_confirmada_em: datetime | None
    assinatura_resposta_texto: str | None
    created_at: datetime

    @field_serializer("data_fim")
    def _serialize_data_fim(self, valor: date | None) -> date | None:
        if valor is None:
            return None
        return _none_se_sentinela(valor)


class ContractWithItemsRead(ContractRead):
    itens: list[ContractItemRead]


class ContractBaixaRequest(BaseModel):
    item_ids: list[int] | None = None  # None = baixa total (todos os itens ativos)
    motivo: str | None = None
    # Obrigatório por item quando o contrato é cobrado por hora (periodicidade "hora"):
    # {contract_item_id: horas_trabalhadas}. Usado para calcular a fatura na baixa.
    horas_por_item: dict[int, Decimal] | None = None


class ContractExtendRequest(BaseModel):
    nova_data_fim: date
    motivo: str | None = None


class ContractCancelRequest(BaseModel):
    motivo: str | None = None


class ContractAddItemsRequest(BaseModel):
    itens: list[ContractItemRequest]
    # O valor do aditivo é sempre calculado a partir do preço cadastrado no
    # estoque do equipamento (ver invoice_service.calcular_valor_item_periodo)
    # — nunca digitado manualmente. Contratos "diária"/"mensal" usam a própria
    # periodicidade do contrato; contratos de cobrança "única" não têm taxa
    # recorrente própria, então precisam informar aqui qual condição usar
    # (diária ou mensal) pra calcular o preço deste item especificamente.
    condicao_cobranca_item: BillingPeriodicity | None = None
    # Vencimento da fatura do aditivo — se omitido, vence hoje. O usuário pode
    # escolher a mesma data de término do contrato ou qualquer outra data.
    data_vencimento_aditivo: date | None = None
    motivo: str | None = None
