from datetime import date, timedelta
from decimal import Decimal


def _create_client(authed_client, documento):
    return authed_client.post(
        "/api/clients", json={"nome": "Cliente Fatura", "tipo": "PF", "documento": documento}
    ).json()


def _create_filial(authed_client, nome):
    return authed_client.post("/api/filiais", json={"nome": nome}).json()


def _create_equipment(authed_client, nome_categoria, filial_id):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipment = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Fatura", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial_id}", json={"quantidade": 1})
    return equipment


def _create_and_activate_contract(
    authed_client, documento, nome_categoria, data_inicio, data_fim, valor_total=None, periodicidade="unica"
):
    cliente = _create_client(authed_client, documento)
    filial = _create_filial(authed_client, f"Filial {nome_categoria}")
    equipamento = _create_equipment(authed_client, nome_categoria, filial["id"])
    payload = {
        "cliente_id": cliente["id"],
        "data_inicio": data_inicio.isoformat(),
        "data_fim": data_fim.isoformat(),
        "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        "periodicidade_cobranca": periodicidade,
    }
    if valor_total is not None:
        payload["valor_total"] = str(valor_total)
    contract = authed_client.post("/api/contracts", json=payload).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    return contract, equipamento


def test_activate_with_valor_total_generates_single_invoice(authed_client):
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract, _ = _create_and_activate_contract(
        authed_client, "111.111.111-01", "Cat Fatura A", inicio, fim, valor_total="1000.00"
    )

    response = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]})
    assert response.status_code == 200
    invoices = response.json()
    assert len(invoices) == 1
    assert invoices[0]["valor"] == "1000.00"
    assert invoices[0]["status"] == "pendente"
    assert invoices[0]["data_vencimento"] == inicio.isoformat()


def test_activate_without_valor_total_generates_no_invoices(authed_client):
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract, _ = _create_and_activate_contract(authed_client, "111.111.111-02", "Cat Fatura B", inicio, fim)

    response = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]})
    assert response.status_code == 200
    assert response.json() == []


def test_monthly_periodicity_generates_multiple_invoices_summing_to_total(authed_client):
    inicio = date.today()
    fim = inicio + timedelta(days=65)
    contract, _ = _create_and_activate_contract(
        authed_client, "111.111.111-03", "Cat Fatura C", inicio, fim, valor_total="300.00", periodicidade="mensal"
    )

    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(invoices) >= 2
    assert sum(Decimal(i["valor"]) for i in invoices) == Decimal("300.00")


def test_daily_periodicity_generates_one_invoice_per_day(authed_client):
    inicio = date.today()
    fim = inicio + timedelta(days=2)  # 3 dias corridos
    contract, _ = _create_and_activate_contract(
        authed_client, "111.111.111-04", "Cat Fatura D", inicio, fim, valor_total="300.00", periodicidade="diaria"
    )

    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(invoices) == 3
    assert sum(Decimal(i["valor"]) for i in invoices) == Decimal("300.00")


def test_invoice_has_items_linked_to_contract_items(authed_client):
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract, equipamento = _create_and_activate_contract(
        authed_client, "111.111.111-05", "Cat Fatura E", inicio, fim, valor_total="500.00"
    )
    invoice = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()[0]

    items_response = authed_client.get(f"/api/invoices/{invoice['id']}/items")
    assert items_response.status_code == 200
    items = items_response.json()
    assert len(items) == 1
    assert items[0]["valor"] == "500.00"


def test_cancel_contract_cancels_pending_invoices(authed_client):
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract, _ = _create_and_activate_contract(
        authed_client, "111.111.111-06", "Cat Fatura F", inicio, fim, valor_total="200.00"
    )

    authed_client.post(f"/api/contracts/{contract['id']}/cancel", json={})

    invoice = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()[0]
    assert invoice["status"] == "cancelada"


def test_baixa_total_does_not_cancel_invoices(authed_client):
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract, _ = _create_and_activate_contract(
        authed_client, "111.111.111-07", "Cat Fatura G", inicio, fim, valor_total="200.00"
    )

    authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={})

    invoice = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()[0]
    assert invoice["status"] == "pendente"
