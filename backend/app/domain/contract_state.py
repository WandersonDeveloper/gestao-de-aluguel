from app.domain.exceptions import InvalidTransitionError
from app.models.contract import ContractStatus

# Transições de status do contrato (seção 4.2 do plano). Extensão de vigência
# não é uma transição de status — ver app/services/contract_service.py.
ALLOWED_TRANSITIONS: dict[ContractStatus, set[ContractStatus]] = {
    ContractStatus.RASCUNHO: {ContractStatus.ATIVO, ContractStatus.CANCELADO},
    ContractStatus.ATIVO: {ContractStatus.VENCIDO, ContractStatus.ENCERRADO, ContractStatus.CANCELADO},
    ContractStatus.VENCIDO: {ContractStatus.ENCERRADO, ContractStatus.CANCELADO, ContractStatus.ATIVO},
    ContractStatus.ENCERRADO: set(),
    ContractStatus.CANCELADO: set(),
}


def assert_valid_transition(atual: ContractStatus, novo: ContractStatus) -> None:
    if novo not in ALLOWED_TRANSITIONS.get(atual, set()):
        raise InvalidTransitionError(f"Transição de contrato inválida: {atual.value} -> {novo.value}")
