import pytest

from app.domain.contract_state import assert_valid_transition
from app.domain.exceptions import InvalidTransitionError
from app.models.contract import ContractStatus as S


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.RASCUNHO, S.ATIVO),
        (S.RASCUNHO, S.CANCELADO),
        (S.ATIVO, S.VENCIDO),
        (S.ATIVO, S.ENCERRADO),
        (S.ATIVO, S.CANCELADO),
        (S.VENCIDO, S.ENCERRADO),
        (S.VENCIDO, S.CANCELADO),
        (S.VENCIDO, S.ATIVO),
    ],
)
def test_allowed_transitions_do_not_raise(atual, novo):
    assert_valid_transition(atual, novo)


@pytest.mark.parametrize(
    "atual,novo",
    [
        (S.RASCUNHO, S.ENCERRADO),
        (S.RASCUNHO, S.VENCIDO),
        (S.ENCERRADO, S.ATIVO),
        (S.CANCELADO, S.ATIVO),
        (S.ATIVO, S.RASCUNHO),
    ],
)
def test_disallowed_transitions_raise(atual, novo):
    with pytest.raises(InvalidTransitionError):
        assert_valid_transition(atual, novo)
