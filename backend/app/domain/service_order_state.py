from app.domain.exceptions import InvalidTransitionError
from app.models.service_order import ServiceOrderStatus

# Transições de status da OS (seção 4.3 do plano).
ALLOWED_TRANSITIONS: dict[ServiceOrderStatus, set[ServiceOrderStatus]] = {
    ServiceOrderStatus.ABERTA: {ServiceOrderStatus.EM_ANDAMENTO, ServiceOrderStatus.CANCELADA},
    ServiceOrderStatus.EM_ANDAMENTO: {ServiceOrderStatus.CONCLUIDA, ServiceOrderStatus.CANCELADA},
    ServiceOrderStatus.CONCLUIDA: set(),
    ServiceOrderStatus.CANCELADA: set(),
}


def assert_valid_transition(atual: ServiceOrderStatus, novo: ServiceOrderStatus) -> None:
    if novo not in ALLOWED_TRANSITIONS.get(atual, set()):
        raise InvalidTransitionError(f"Transição de OS inválida: {atual.value} -> {novo.value}")
