from datetime import date, timedelta

from sqlalchemy import select

from app.models.invoice import Invoice
from app.services import contract_service, invoice_service


def _create_contract_payload(cliente_id, equipamento_id, filial_id, data_inicio, data_fim=None, **kwargs):
    payload = {
        "cliente_id": cliente_id,
        "data_inicio": data_inicio.isoformat(),
        "itens": [{"equipamento_id": equipamento_id, "filial_id": filial_id, "quantidade": 1}],
        **kwargs,
    }
    if data_fim is not None:
        payload["data_fim"] = data_fim.isoformat()
    return payload


def test_create_open_ended_contract_has_null_data_fim(authed_client, cliente, equipamento, filial):
    inicio = date.today()
    response = authed_client.post(
        "/api/contracts",
        json=_create_contract_payload(
            cliente["id"], equipamento["id"], filial["id"], inicio, periodicidade_cobranca="mensal"
        ),
    )
    assert response.status_code == 201
    assert response.json()["data_fim"] is None


def test_open_ended_contract_rejects_unica_periodicidade(authed_client, cliente, equipamento, filial):
    inicio = date.today()
    response = authed_client.post(
        "/api/contracts",
        json=_create_contract_payload(
            cliente["id"], equipamento["id"], filial["id"], inicio, periodicidade_cobranca="unica"
        ),
    )
    assert response.status_code == 409


def test_open_ended_contract_generates_first_invoice_on_activate(authed_client, cliente, equipamento, filial):
    inicio = date.today()
    contract = authed_client.post(
        "/api/contracts",
        json=_create_contract_payload(
            cliente["id"],
            equipamento["id"],
            filial["id"],
            inicio,
            periodicidade_cobranca="mensal",
            valor_recorrente="1000.00",
        ),
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(invoices) == 1
    assert invoices[0]["valor"] == "1000.00"
    assert invoices[0]["data_vencimento"] == inicio.isoformat()


def test_open_ended_contract_without_valor_recorrente_generates_no_invoice(
    authed_client, cliente, equipamento, filial
):
    inicio = date.today()
    contract = authed_client.post(
        "/api/contracts",
        json=_create_contract_payload(
            cliente["id"], equipamento["id"], filial["id"], inicio, periodicidade_cobranca="mensal"
        ),
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert invoices == []


def test_open_ended_contract_never_expires(authed_client, db_session, cliente, equipamento, filial):
    inicio = date.today() - timedelta(days=400)
    contract = authed_client.post(
        "/api/contracts",
        json=_create_contract_payload(
            cliente["id"],
            equipamento["id"],
            filial["id"],
            inicio,
            periodicidade_cobranca="mensal",
            valor_recorrente="1000.00",
        ),
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    afetados = contract_service.mark_expired_contracts(db_session)

    assert not any(c.id == contract["id"] for c in afetados)
    response = authed_client.get(f"/api/contracts/{contract['id']}")
    assert response.json()["status"] == "ativo"


def test_cannot_extend_open_ended_contract(authed_client, cliente, equipamento, filial):
    inicio = date.today()
    contract = authed_client.post(
        "/api/contracts",
        json=_create_contract_payload(
            cliente["id"],
            equipamento["id"],
            filial["id"],
            inicio,
            periodicidade_cobranca="mensal",
            valor_recorrente="1000.00",
        ),
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.post(
        f"/api/contracts/{contract['id']}/extend",
        json={"nova_data_fim": (inicio + timedelta(days=30)).isoformat()},
    )
    assert response.status_code == 409


def test_generate_next_recurring_invoices_creates_next_period(
    authed_client, db_session, cliente, equipamento, filial
):
    inicio = date.today()
    contract = authed_client.post(
        "/api/contracts",
        json=_create_contract_payload(
            cliente["id"],
            equipamento["id"],
            filial["id"],
            inicio,
            periodicidade_cobranca="mensal",
            valor_recorrente="1000.00",
        ),
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    # Simula o mês já ter passado, adiantando a data de vencimento da
    # primeira fatura para o passado — sem isso teríamos que esperar um mês
    # real para o próximo período ficar "atrasado" e ser gerado.
    invoice = db_session.scalars(select(Invoice).where(Invoice.contrato_id == contract["id"])).one()
    invoice.data_vencimento = date.today() - timedelta(days=35)
    db_session.flush()

    geradas = invoice_service.generate_next_recurring_invoices(db_session)

    assert any(f.contrato_id == contract["id"] for f in geradas)
    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(invoices) == 2
    assert sorted(i["data_vencimento"] for i in invoices)[0] == invoice.data_vencimento.isoformat()


def test_generate_next_recurring_invoices_skips_fixed_term_contracts(authed_client, db_session):
    cliente = authed_client.post(
        "/api/clients", json={"nome": "Cliente Fixo", "tipo": "PF", "documento": "999.111.222-01"}
    ).json()
    filial = authed_client.post("/api/filiais", json={"nome": "Filial Fixa"}).json()
    category = authed_client.post("/api/equipment-categories", json={"nome": "Cat Fixa"}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equip Fixo", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 1})

    inicio = date.today()
    fim = inicio + timedelta(days=65)
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "periodicidade_cobranca": "mensal",
            "valor_total": "300.00",
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    invoices_antes = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()

    geradas = invoice_service.generate_next_recurring_invoices(db_session)

    assert not any(f.contrato_id == contract["id"] for f in geradas)
    invoices_depois = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(invoices_depois) == len(invoices_antes)
