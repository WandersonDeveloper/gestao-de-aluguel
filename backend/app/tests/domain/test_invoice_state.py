import pytest

from app.domain.exceptions import InvalidTransitionError
from app.domain.invoice_state import assert_valid_transition
from app.models.invoice import InvoiceStatus as S


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.PENDENTE, S.PAGA),
        (S.PENDENTE, S.ATRASADA),
        (S.PENDENTE, S.CANCELADA),
        (S.ATRASADA, S.PAGA),
        (S.ATRASADA, S.CANCELADA),
    ],
)
def test_allowed_transitions_do_not_raise(atual, novo):
    assert_valid_transition(atual, novo)


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.PAGA, S.PENDENTE),
        (S.CANCELADA, S.PENDENTE),
        (S.PENDENTE, S.PENDENTE),
        (S.ATRASADA, S.PENDENTE),
    ],
)
def test_disallowed_transitions_raise(atual, novo):
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition(atual, novo)
