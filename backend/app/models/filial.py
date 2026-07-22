from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class Filial(Base):
    __tablename__ = "filiais"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    endereco: Mapped[str | None] = mapped_column(String(500))
    telefone: Mapped[str | None] = mapped_column(String(32))
    observacoes: Mapped[str | None] = mapped_column(String(2000))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
