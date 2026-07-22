from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base

if TYPE_CHECKING:
    from app.models.filial import Filial


class EquipmentStock(Base):
    """Quantidade e valores de um equipamento numa filial específica.

    Um mesmo equipamento (cadastro único: nome/categoria/marca/modelo) pode
    existir em várias filiais ao mesmo tempo, cada uma com sua própria
    quantidade em estoque e seus próprios valores de locação (o preço pode
    variar por unidade/região). Reservas de contrato (`ContractItem`) sempre
    miram um par (equipamento, filial) específico — ver contract_service.
    """

    __tablename__ = "equipment_stock"
    __table_args__ = (
        UniqueConstraint("equipamento_id", "filial_id", name="uq_equipment_stock_equipamento_filial"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False)
    filial_id: Mapped[int] = mapped_column(ForeignKey("filiais.id"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    valor_diario: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    valor_mensal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    valor_hora: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    filial: Mapped["Filial"] = relationship()
