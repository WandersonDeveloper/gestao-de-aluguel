from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.contract import ContractSignatureStatus
from app.models.contract_amendment import ContractAmendmentType
from app.schemas.contract import ContractItemRead


class ContractAmendmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    contrato_id: int
    usuario_id: int
    tipo: ContractAmendmentType
    data_anterior: date | None
    data_nova: date | None
    motivo: str | None
    created_at: datetime
    assinatura_status: ContractSignatureStatus
    assinatura_resposta_texto: str | None
    assinatura_confirmada_em: datetime | None
    itens: list[ContractItemRead] = []
