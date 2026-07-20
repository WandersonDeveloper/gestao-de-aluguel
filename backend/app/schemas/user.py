from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.user import UserRole


class UserBase(BaseModel):
    nome: str
    email: str
    papel: UserRole = UserRole.OPERADOR


class UserCreate(UserBase):
    senha: str


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ativo: bool
    created_at: datetime
