from datetime import timedelta


def test_create_contract_success(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    response = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "rascunho"
    assert body["cliente_id"] == cliente["id"]


def test_create_contract_requires_existing_client(authed_client, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    response = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": 999999,
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    )
    assert response.status_code == 404


def test_create_contract_requires_existing_equipment(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    response = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": 999999, "filial_id": filial["id"], "quantidade": 1}],
        },
    )
    assert response.status_code == 404


def test_create_contract_requires_stock_in_filial(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    category = authed_client.post("/api/equipment-categories", json={"nome": "Categoria Sem Estoque"}).json()
    equipment = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Sem Estoque", "categoria_id": category["id"]}
    ).json()
    response = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipment["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    )
    assert response.status_code == 404


def test_create_contract_requires_at_least_one_equipment(authed_client, cliente, periodo_atual):
    inicio, fim = periodo_atual
    response = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [],
        },
    )
    assert response.status_code == 409


def test_overlapping_dates_for_same_equipment_conflicts(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    payload = {
        "cliente_id": cliente["id"],
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
    }
    first = authed_client.post("/api/contracts", json=payload)
    assert first.status_code == 201

    # Segundo contrato com período sobreposto para o mesmo equipamento na mesma filial.
    overlapping_payload = dict(payload)
    overlapping_payload["data_inicio"] = (inicio + timedelta(days=2)).isoformat()
    overlapping_payload["data_fim"] = (fim + timedelta(days=2)).isoformat()
    second = authed_client.post("/api/contracts", json=overlapping_payload)
    assert second.status_code == 409


def test_non_overlapping_dates_for_same_equipment_succeeds(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    payload = {
        "cliente_id": cliente["id"],
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
    }
    first = authed_client.post("/api/contracts", json=payload)
    assert first.status_code == 201

    # Período totalmente após o fim do primeiro contrato: não deve conflitar.
    next_payload = dict(payload)
    next_payload["data_inicio"] = (fim + timedelta(days=1)).isoformat()
    next_payload["data_fim"] = (fim + timedelta(days=6)).isoformat()
    second = authed_client.post("/api/contracts", json=next_payload)
    assert second.status_code == 201


def test_get_contract_returns_items(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    created = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    ).json()

    response = authed_client.get(f"/api/contracts/{created['id']}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["itens"]) == 1
    assert body["itens"][0]["equipamento_id"] == equipamento["id"]
    assert body["itens"][0]["filial_id"] == filial["id"]
    assert body["itens"][0]["status"] == "ativo"


def test_contracts_require_authentication(client):
    response = client.get("/api/contracts")
    assert response.status_code == 401
