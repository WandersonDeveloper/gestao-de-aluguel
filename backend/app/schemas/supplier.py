from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SupplierBase(BaseModel):
    nome: str
    documento: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    observacoes: str | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    nome: str | None = None
    documento: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None
    observacoes: str | None = None


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
