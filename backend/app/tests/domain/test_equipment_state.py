import pytest

from app.domain.equipment_state import assert_valid_transition
from app.domain.exceptions import InvalidTransitionError
from app.models.equipment import EquipmentStatus as S


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.DISPONIVEL, S.RESERVADO),
        (S.DISPONIVEL, S.MANUTENCAO),
        (S.RESERVADO, S.ALUGADO),
        (S.RESERVADO, S.DISPONIVEL),
        (S.ALUGADO, S.DISPONIVEL),
        (S.ALUGADO, S.MANUTENCAO),
        (S.MANUTENCAO, S.DISPONIVEL),
    ],
)
def test_allowed_transitions_do_not_raise(atual, novo):
    assert_valid_transition(atual, novo)


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.DISPONIVEL, S.ALUGADO),
        (S.MANUTENCAO, S.ALUGADO),
        (S.MANUTENCAO, S.RESERVADO),
        (S.ALUGADO, S.RESERVADO),
        (S.DISPONIVEL, S.DISPONIVEL),
    ],
)
def test_disallowed_transitions_raise(atual, novo):
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition(atual, novo)
