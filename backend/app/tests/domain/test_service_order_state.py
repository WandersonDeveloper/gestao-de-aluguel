import pytest

from app.domain.exceptions import InvalidTransitionError
from app.domain.service_order_state import assert_valid_transition
from app.models.service_order import ServiceOrderStatus as S


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.ABERTA, S.EM_ANDAMENTO),
        (S.ABERTA, S.CANCELADA),
        (S.EM_ANDAMENTO, S.CONCLUIDA),
        (S.EM_ANDAMENTO, S.CANCELADA),
    ],
)
def test_allowed_transitions_do_not_raise(atual, novo):
    assert_valid_transition(atual, novo)


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.ABERTA, S.CONCLUIDA),
        (S.CONCLUIDA, S.EM_ANDAMENTO),
        (S.CANCELADA, S.EM_ANDAMENTO),
        (S.ABERTA, S.ABERTA),
    ],
)
def test_disallowed_transitions_raise(atual, novo):
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition(atual, novo)
