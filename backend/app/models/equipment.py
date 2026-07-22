import enum
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.equipment_category import EquipmentCategory
from app.models.equipment_stock import EquipmentStock


class EquipmentStatus(str, enum.Enum):
    DISPONIVEL = "disponivel"
    RESERVADO = "reservado"
    ALUGADO = "alugado"
    MANUTENCAO = "manutencao"


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("equipment_categories.id"), nullable=False)
    marca: Mapped[str | None] = mapped_column(String(255))
    modelo: Mapped[str | None] = mapped_column(String(255))
    identificador: Mapped[str | None] = mapped_column(String(100), unique=True)
    status: Mapped[EquipmentStatus] = mapped_column(
        SAEnum(EquipmentStatus, name="equipment_status"),
        default=EquipmentStatus.DISPONIVEL,
        server_default=EquipmentStatus.DISPONIVEL.name,
        nullable=False,
    )
    localizacao: Mapped[str | None] = mapped_column(String(255))
    observacoes: Mapped[str | None] = mapped_column(String(2000))
    atributos_extra: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    fotos: Mapped[list] = mapped_column(JSONB, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    categoria: Mapped[EquipmentCategory] = relationship()
    # Quantidade e valores de locação por filial (ver EquipmentStock): um mesmo
    # equipamento pode estar disponível em várias filiais simultaneamente, cada
    # uma com sua própria quantidade e preço. `status` acima só é significativo
    # para equipamento "serializado" (uma única filial, quantidade 1) — ver
    # `is_estoque` e `regras-de-negocio.md`.
    estoques: Mapped[list[EquipmentStock]] = relationship(cascade="all, delete-orphan")

    @property
    def quantidade_total(self) -> int:
        return sum(estoque.quantidade for estoque in self.estoques)

    @property
    def is_estoque(self) -> bool:
        return self.quantidade_total > 1 or len(self.estoques) > 1
