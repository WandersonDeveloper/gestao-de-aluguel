from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FilialBase(BaseModel):
    nome: str
    endereco: str | None = None
    telefone: str | None = None
    observacoes: str | None = None


class FilialCreate(FilialBase):
    pass


class FilialUpdate(BaseModel):
    nome: str | None = None
    endereco: str | None = None
    telefone: str | None = None
    observacoes: str | None = None


class FilialRead(FilialBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
