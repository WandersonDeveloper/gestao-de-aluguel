import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base
from app.models.equipment_category import EquipmentCategory


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
    valor_diario: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    valor_mensal: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    localizacao: Mapped[str | None] = mapped_column(String(255))
    observacoes: Mapped[str | None] = mapped_column(String(2000))
    atributos_extra: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    categoria: Mapped[EquipmentCategory] = relationship()
