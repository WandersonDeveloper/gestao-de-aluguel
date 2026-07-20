import enum
from datetime import datetime

from sqlalchemy import String
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class ClientType(str, enum.Enum):
    PF = "PF"
    PJ = "PJ"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[ClientType] = mapped_column(SAEnum(ClientType, name="client_type"), nullable=False)
    documento: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    telefone: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    endereco: Mapped[str | None] = mapped_column(String(500))
    observacoes: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
