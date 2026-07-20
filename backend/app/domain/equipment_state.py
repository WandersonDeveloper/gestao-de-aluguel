from app.domain.exceptions import InvalidTransitionError
from app.models.equipment import EquipmentStatus

# Transições permitidas da máquina de estado do equipamento (seção 4.1 do plano).
# "manutenção -> alugado" nunca é permitido diretamente: sempre passa por "disponível".
ALLOWED_TRANSITIONS: dict[EquipmentStatus, set[EquipmentStatus]] = {
    EquipmentStatus.DISPONIVEL: {EquipmentStatus.RESERVADO, EquipmentStatus.MANUTENCAO},
    EquipmentStatus.RESERVADO: {EquipmentStatus.ALUGADO, EquipmentStatus.DISPONIVEL},
    EquipmentStatus.ALUGADO: {EquipmentStatus.DISPONIVEL, EquipmentStatus.MANUTENCAO},
    EquipmentStatus.MANUTENCAO: {EquipmentStatus.DISPONIVEL},
}


def assert_valid_transition(atual: EquipmentStatus, novo: EquipmentStatus) -> None:
    if novo not in ALLOWED_TRANSITIONS.get(atual, set()):
        raise InvalidTransitionError(f"Transição inválida: {atual.value} -> {novo.value}")
