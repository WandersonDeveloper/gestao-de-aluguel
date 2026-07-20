from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.client import ClientType


class ClientBase(BaseModel):
    nome: str
    tipo: ClientType
    documento: str
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    observacoes: str | None = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    nome: str | None = None
    tipo: ClientType | None = None
    documento: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    observacoes: str | None = None


class ClientRead(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
