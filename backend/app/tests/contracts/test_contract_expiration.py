from datetime import date, timedelta

from app.models.contract import Contract, ContractStatus
from app.services import contract_service


def _create_and_activate(authed_client, cliente, equipamento, inicio, fim):
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "equipamento_ids": [equipamento["id"]],
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    return contract


def test_mark_expired_contracts_transitions_past_due_active_contract(
    authed_client, db_session, cliente, equipamento
):
    inicio = date.today() - timedelta(days=10)
    fim = date.today() - timedelta(days=5)
    contract = _create_and_activate(authed_client, cliente, equipamento, inicio, fim)

    afetados = contract_service.mark_expired_contracts(db_session)

    assert any(c.id == contract["id"] for c in afetados)
    atualizado = db_session.get(Contract, contract["id"])
    assert atualizado.status == ContractStatus.VENCIDO


def test_mark_expired_contracts_does_not_touch_future_contract(
    authed_client, db_session, cliente, equipamento, periodo_futuro
):
    inicio, fim = periodo_futuro
    contract = _create_and_activate(authed_client, cliente, equipamento, inicio, fim)

    afetados = contract_service.mark_expired_contracts(db_session)

    assert not any(c.id == contract["id"] for c in afetados)
    response = authed_client.get(f"/api/contracts/{contract['id']}")
    assert response.json()["status"] == "ativo"


def test_mark_expired_contracts_does_not_touch_draft_contract(authed_client, db_session, cliente, equipamento):
    inicio = date.today() - timedelta(days=10)
    fim = date.today() - timedelta(days=5)
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "equipamento_ids": [equipamento["id"]],
        },
    ).json()

    afetados = contract_service.mark_expired_contracts(db_session)

    assert not any(c.id == contract["id"] for c in afetados)
    response = authed_client.get(f"/api/contracts/{contract['id']}")
    assert response.json()["status"] == "rascunho"
