from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.service_order import ServiceOrderPriority, ServiceOrderStatus, ServiceOrderType


class ServiceOrderCreate(BaseModel):
    equipamento_id: int
    contrato_id: int | None = None
    tipo: ServiceOrderType
    descricao: str
    prioridade: ServiceOrderPriority = ServiceOrderPriority.MEDIA


class ServiceOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipamento_id: int
    contrato_id: int | None
    tipo: ServiceOrderType
    descricao: str
    prioridade: ServiceOrderPriority
    status: ServiceOrderStatus
    observacoes: str | None
    data_abertura: datetime
    data_conclusao: datetime | None


class ServiceOrderCloseRequest(BaseModel):
    observacoes: str | None = None
