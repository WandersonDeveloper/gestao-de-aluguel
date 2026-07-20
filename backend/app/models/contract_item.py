import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ExcludeConstraint
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
    data_inicio_item: Mapped[date] = mapped_column(Date, nullable=False)
    data_fim_item: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[ContractItemStatus] = mapped_column(
        SAEnum(ContractItemStatus, name="contract_item_status"),
        default=ContractItemStatus.ATIVO,
        server_default=ContractItemStatus.ATIVO.name,
        nullable=False,
    )
    valor_item: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    __table_args__ = (
        # Garantia no nível do banco: um equipamento não pode ter dois itens de
        # contrato "ativo" (ainda não devolvido) com períodos sobrepostos.
        ExcludeConstraint(
            (text("equipamento_id"), "="),
            (text("daterange(data_inicio_item, data_fim_item, '[]')"), "&&"),
            where=text("status = 'ATIVO'"),
            using="gist",
            name="contract_items_no_overlap",
        ),
    )
