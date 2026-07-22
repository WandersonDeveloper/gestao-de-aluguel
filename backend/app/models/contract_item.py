import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ContractItemStatus(str, enum.Enum):
    ATIVO = "ativo"
    DEVOLVIDO = "devolvido"


class ContractItem(Base):
    __tablename__ = "contract_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    contrato_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    # De qual filial a quantidade abaixo é reservada — um equipamento pode ter
    # estoque em várias filiais (EquipmentStock), então a reserva precisa dizer
    # de qual delas está tirando quantidade.
    filial_id: Mapped[int] = mapped_column(ForeignKey("filiais.id"), nullable=False)
    data_inicio_item: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim_item: Mapped[date] = mapped_column(Date, nullable=False)
    # Quantas unidades desse equipamento este item reserva (equipamento "de estoque",
    # quantidade_total > 1, pode ter vários itens ativos simultâneos de contratos
    # diferentes, desde que a soma não ultrapasse o estoque — ver contract_service).
    quantidade: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    status: Mapped[ContractItemStatus] = mapped_column(
        SAEnum(ContractItemStatus, name="contract_item_status"),
        default=ContractItemStatus.ATIVO,
        server_default=ContractItemStatus.ATIVO.name,
        nullable=False,
    )
    valor_item: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    horas_trabalhadas: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # Preenchido só quando o item veio de um aditivo (ver contract_service.add_items) —
    # deixa explícito, sem ambiguidade de datas, qual aditivo adicionou qual item
    # (ver ContractAmendment.itens, usado no histórico de aditivos do frontend).
    amendment_id: Mapped[int | None] = mapped_column(ForeignKey("contract_amendments.id"), nullable=True)

    # Não há mais EXCLUDE constraint de sobreposição de datas aqui: com quantidade
    # variável por item, "conflito" não é mais uma simples exclusão binária (dois
    # itens do mesmo equipamento PODEM se sobrepor, contanto que a soma das
    # quantidades não ultrapasse equipment.quantidade_total). Essa checagem agora
    # é feita em contract_service, com um lock de linha no equipamento
    # (SELECT ... FOR UPDATE) para evitar corrida entre requisições concorrentes.
