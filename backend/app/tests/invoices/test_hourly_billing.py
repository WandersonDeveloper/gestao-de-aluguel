from datetime import date, timedelta
from decimal import Decimal


def _create_filial(authed_client, nome):
    return authed_client.post("/api/filiais", json={"nome": nome}).json()


def _create_equipment(authed_client, nome_categoria, filial_id, valor_hora=None):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipment = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Hora", "categoria_id": category["id"]}
    ).json()
    stock_payload = {"quantidade": 1}
    if valor_hora is not None:
        stock_payload["valor_hora"] = str(valor_hora)
    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial_id}", json=stock_payload)
    return equipment


def _create_client(authed_client, documento):
    return authed_client.post(
        "/api/clients", json={"nome": "Cliente Hora", "tipo": "PF", "documento": documento}
    ).json()


def test_activate_hourly_contract_generates_no_invoice(authed_client):
    filial = _create_filial(authed_client, "Filial Hora A")
    cliente = _create_client(authed_client, "777.000.111-01")
    equipamento = _create_equipment(authed_client, "Cat Hora A", filial["id"], valor_hora="50.00")
    inicio = date.today()
    fim = inicio + timedelta(days=5)

    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "periodicidade_cobranca": "hora",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert invoices == []


def test_baixa_with_hours_generates_invoice(authed_client):
    filial = _create_filial(authed_client, "Filial Hora B")
    cliente = _create_client(authed_client, "777.000.111-02")
    equipamento = _create_equipment(authed_client, "Cat Hora B", filial["id"], valor_hora="50.00")
    inicio = date.today()
    fim = inicio + timedelta(days=5)

    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "periodicidade_cobranca": "hora",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    itens = authed_client.get(f"/api/contracts/{contract['id']}").json()["itens"]
    item_id = itens[0]["id"]

    response = authed_client.post(
        f"/api/contracts/{contract['id']}/baixa",
        json={"horas_por_item": {str(item_id): "12.5"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "encerrado"

    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(invoices) == 1
    assert Decimal(invoices[0]["valor"]) == Decimal("625.00")  # 12.5h * 50.00


def test_baixa_hourly_without_hours_is_rejected(authed_client):
    filial = _create_filial(authed_client, "Filial Hora C")
    cliente = _create_client(authed_client, "777.000.111-03")
    equipamento = _create_equipment(authed_client, "Cat Hora C", filial["id"], valor_hora="50.00")
    inicio = date.today()
    fim = inicio + timedelta(days=5)

    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "periodicidade_cobranca": "hora",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={})
    assert response.status_code == 409


def test_baixa_hourly_without_valor_hora_is_rejected(authed_client):
    filial = _create_filial(authed_client, "Filial Hora D")
    cliente = _create_client(authed_client, "777.000.111-04")
    equipamento = _create_equipment(authed_client, "Cat Hora D", filial["id"])  # sem valor_hora
    inicio = date.today()
    fim = inicio + timedelta(days=5)

    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "periodicidade_cobranca": "hora",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    itens = authed_client.get(f"/api/contracts/{contract['id']}").json()["itens"]
    item_id = itens[0]["id"]

    response = authed_client.post(
        f"/api/contracts/{contract['id']}/baixa",
        json={"horas_por_item": {str(item_id): "10"}},
    )
    assert response.status_code == 409


def test_partial_baixa_hourly_only_requires_hours_for_selected_items(authed_client):
    filial = _create_filial(authed_client, "Filial Hora E")
    cliente = _create_client(authed_client, "777.000.111-05")
    cat = authed_client.post("/api/equipment-categories", json={"nome": "Cat Hora E"}).json()
    eq1 = authed_client.post(
        "/api/equipment", json={"nome": "Equip Hora 1", "categoria_id": cat["id"]}
    ).json()
    eq2 = authed_client.post(
        "/api/equipment", json={"nome": "Equip Hora 2", "categoria_id": cat["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{eq1['id']}/estoque/{filial['id']}", json={"quantidade": 1, "valor_hora": "40.00"})
    authed_client.put(f"/api/equipment/{eq2['id']}/estoque/{filial['id']}", json={"quantidade": 1, "valor_hora": "60.00"})
    inicio = date.today()
    fim = inicio + timedelta(days=5)

    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [
                {"equipamento_id": eq1["id"], "filial_id": filial["id"], "quantidade": 1},
                {"equipamento_id": eq2["id"], "filial_id": filial["id"], "quantidade": 1},
            ],
            "periodicidade_cobranca": "hora",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    itens = authed_client.get(f"/api/contracts/{contract['id']}").json()["itens"]
    item_eq1 = next(i for i in itens if i["equipamento_id"] == eq1["id"])

    response = authed_client.post(
        f"/api/contracts/{contract['id']}/baixa",
        json={"item_ids": [item_eq1["id"]], "horas_por_item": {str(item_eq1["id"]): "10"}},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ativo"

    invoices = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(invoices) == 1
    assert Decimal(invoices[0]["valor"]) == Decimal("400.00")  # 10h * 40.00
