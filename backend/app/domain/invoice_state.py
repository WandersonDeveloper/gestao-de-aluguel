from app.domain.exceptions import InvalidTransitionError
from app.models.invoice import InvoiceStatus

# Transições de status da fatura (seção 4.4 do plano).
ALLOWED_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.PENDENTE: {InvoiceStatus.PAGA, InvoiceStatus.ATRASADA, InvoiceStatus.CANCELADA},
    InvoiceStatus.ATRASADA: {InvoiceStatus.PAGA, InvoiceStatus.CANCELADA},
    InvoiceStatus.PAGA: set(),
    InvoiceStatus.CANCELADA: set(),
}


def assert_valid_transition(atual: InvoiceStatus, novo: InvoiceStatus) -> None:
    if novo not in ALLOWED_TRANSITIONS.get(atual, set()):
        raise InvalidTransitionError(f"Transição de fatura inválida: {atual.value} -> {novo.value}")
