import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ContractStatus(str, enum.Enum):
    RASCUNHO = "rascunho"
    ATIVO = "ativo"
    VENCIDO = "vencido"
    ENCERRADO = "encerrado"
    CANCELADO = "cancelado"


class BillingPeriodicity(str, enum.Enum):
    UNICA = "unica"
    MENSAL = "mensal"
    DIARIA = "diaria"
    HORA = "hora"


class ContractType(str, enum.Enum):
    LOCACAO = "locacao"
    SERVICO = "servico"


class ContractSignatureStatus(str, enum.Enum):
    NAO_ENVIADO = "nao_enviado"
    AGUARDANDO_CONFIRMACAO = "aguardando_confirmacao"
    CONFIRMADO = "confirmado"
    RECUSADO = "recusado"


# Contratos "em aberto" (sem data de término definida) armazenam essa data
# sentinela em `data_fim` em vez de NULL — evita tornar `data_fim_item` também
# opcional em `contract_items`, o que exigiria reescrever toda a lógica de
# soma/overlap de estoque (ver contract_service, contract_item_repository)
# para tratar NULL como "infinito". Como a sentinela é muito distante no
# futuro, `list_expirable` (data_fim < hoje) nunca a seleciona — contratos em
# aberto simplesmente não expiram sozinhos. A tradução sentinela <-> None
# acontece só na borda da API (ver ContractRead / contract_service).
OPEN_ENDED_SENTINEL_DATE = date(2099, 12, 31)


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    data_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ContractStatus] = mapped_column(
        SAEnum(ContractStatus, name="contract_status"),
        default=ContractStatus.RASCUNHO,
        server_default=ContractStatus.RASCUNHO.name,
        nullable=False,
    )
    # Define o modelo de cláusulas usado ao gerar o documento em PDF (ver
    # contract_document_service) — locação de equipamento vs. prestação de
    # serviço com operação. É uma escolha de negócio feita na criação do
    # contrato, não algo recalculado depois.
    tipo: Mapped[ContractType] = mapped_column(
        SAEnum(ContractType, name="contract_type"),
        default=ContractType.LOCACAO,
        server_default=ContractType.LOCACAO.name,
        nullable=False,
    )
    periodicidade_cobranca: Mapped[BillingPeriodicity] = mapped_column(
        SAEnum(BillingPeriodicity, name="billing_periodicity"),
        default=BillingPeriodicity.UNICA,
        server_default=BillingPeriodicity.UNICA.name,
        nullable=False,
    )
    valor_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    # Valor cobrado a cada período (mensal/diária) em contratos "em aberto"
    # (data_fim == OPEN_ENDED_SENTINEL_DATE) — ver invoice_service.
    # generate_next_recurring_invoices. Não usado em contratos de prazo fixo,
    # que continuam dividindo valor_total pelo período conhecido.
    valor_recorrente: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    observacoes: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Confirmação de aceite via WhatsApp (ver contract_signature_service) — sem
    # histórico de múltiplos reenvios, reenviar sobrescreve o estado anterior.
    assinatura_status: Mapped[ContractSignatureStatus] = mapped_column(
        SAEnum(ContractSignatureStatus, name="contract_signature_status"),
        default=ContractSignatureStatus.NAO_ENVIADO,
        server_default=ContractSignatureStatus.NAO_ENVIADO.name,
        nullable=False,
    )
    assinatura_mensagem_enviada: Mapped[str | None] = mapped_column(String(2000))
    assinatura_enviada_em: Mapped[datetime | None] = mapped_column()
    assinatura_resposta_texto: Mapped[str | None] = mapped_column(String(500))
    # Nome mantido por compatibilidade — na prática é "respondida_em": também
    # é preenchido quando o cliente recusa (assinatura_status = RECUSADO), não
    # só na confirmação.
    assinatura_confirmada_em: Mapped[datetime | None] = mapped_column()
    assinatura_comprovante_key: Mapped[str | None] = mapped_column(String(255))

    @property
    def is_em_aberto(self) -> bool:
        return self.data_fim >= OPEN_ENDED_SENTINEL_DATE
