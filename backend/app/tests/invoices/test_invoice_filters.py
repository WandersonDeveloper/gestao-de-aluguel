from datetime import date, timedelta


def _create_and_activate_contract(authed_client, documento, nome_categoria, valor_total="500.00"):
    cliente = authed_client.post(
        "/api/clients", json={"nome": "Cliente Filtro", "tipo": "PF", "documento": documento}
    ).json()
    filial = authed_client.post("/api/filiais", json={"nome": f"Filial {nome_categoria}"}).json()
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Filtro", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 1})
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": valor_total,
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    return cliente, contract


def test_list_invoices_filters_by_cliente_id(authed_client):
    cliente_a, contract_a = _create_and_activate_contract(authed_client, "333.222.111-01", "Cat Filtro A")
    cliente_b, contract_b = _create_and_activate_contract(authed_client, "333.222.111-02", "Cat Filtro B")

    faturas_a = authed_client.get("/api/invoices", params={"cliente_id": cliente_a["id"]}).json()
    assert len(faturas_a) >= 1
    assert all(f["contrato_id"] == contract_a["id"] for f in faturas_a)

    faturas_b = authed_client.get("/api/invoices", params={"cliente_id": cliente_b["id"]}).json()
    assert len(faturas_b) >= 1
    assert all(f["contrato_id"] == contract_b["id"] for f in faturas_b)
