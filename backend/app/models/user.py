import enum
from datetime import datetime

from sqlalchemy import Boolean, String, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.config.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERADOR = "operador"
    FINANCEIRO = "financeiro"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    papel: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role"),
        default=UserRole.OPERADOR,
        server_default=UserRole.OPERADOR.name,
        nullable=False,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
