import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ServiceOrderType(str, enum.Enum):
    PREVENTIVA = "preventiva"
    CORRETIVA = "corretiva"


class ServiceOrderPriority(str, enum.Enum):
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"


class ServiceOrderStatus(str, enum.Enum):
    ABERTA = "aberta"
    EM_ANDAMENTO = "em_andamento"
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class ServiceOrder(Base):
    __tablename__ = "service_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipamento_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), nullable=False)
    contrato_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))
    tipo: Mapped[ServiceOrderType] = mapped_column(SAEnum(ServiceOrderType, name="service_order_type"), nullable=False)
    descricao: Mapped[str] = mapped_column(String(2000), nullable=False)
    prioridade: Mapped[ServiceOrderPriority] = mapped_column(
        SAEnum(ServiceOrderPriority, name="service_order_priority"),
        default=ServiceOrderPriority.MEDIA,
        server_default=ServiceOrderPriority.MEDIA.name,
        nullable=False,
    )
    status: Mapped[ServiceOrderStatus] = mapped_column(
        SAEnum(ServiceOrderStatus, name="service_order_status"),
        default=ServiceOrderStatus.ABERTA,
        server_default=ServiceOrderStatus.ABERTA.name,
        nullable=False,
    )
    observacoes: Mapped[str | None] = mapped_column(String(2000))
    data_abertura: Mapped[datetime] = mapped_column(server_default=func.now())
    data_conclusao: Mapped[datetime | None] = mapped_column()

    __table_args__ = (
        # Um equipamento não pode ter duas OS em aberto (aberta/em_andamento) ao mesmo tempo.
        Index(
            "service_orders_one_open_per_equipamento",
            "equipamento_id",
            unique=True,
            postgresql_where=text("status IN ('ABERTA', 'EM_ANDAMENTO')"),
        ),
    )
