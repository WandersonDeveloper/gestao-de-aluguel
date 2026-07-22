from datetime import timedelta


def _create_stock_equipment(authed_client, nome_categoria, filial_id, quantidade):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipment = authed_client.post(
        "/api/equipment", json={"nome": "Andaime Estoque", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial_id}", json={"quantidade": quantidade})
    return equipment


def _contract_payload(cliente_id, equipamento_id, filial_id, quantidade, inicio, fim):
    return {
        "cliente_id": cliente_id,
        "data_inicio": inicio.isoformat(),
        "data_fim": fim.isoformat(),
        "itens": [{"equipamento_id": equipamento_id, "filial_id": filial_id, "quantidade": quantidade}],
    }


def test_partial_reservations_within_stock_succeed(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 1", filial["id"], quantidade=10)

    primeiro = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 4, inicio, fim)
    )
    assert primeiro.status_code == 201

    segundo = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 6, inicio, fim)
    )
    assert segundo.status_code == 201


def test_partial_reservations_exceeding_stock_conflicts(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 2", filial["id"], quantidade=10)

    primeiro = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 4, inicio, fim)
    )
    assert primeiro.status_code == 201

    segundo = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 7, inicio, fim)
    )
    assert segundo.status_code == 409


def test_same_equipment_different_filiais_have_independent_capacity(authed_client, cliente, periodo_atual):
    inicio, fim = periodo_atual
    filial_a = authed_client.post("/api/filiais", json={"nome": "Filial Independente A"}).json()
    filial_b = authed_client.post("/api/filiais", json={"nome": "Filial Independente B"}).json()

    category = authed_client.post("/api/equipment-categories", json={"nome": "Categoria Multi-Filial"}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Andaime Multi-Filial", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial_a['id']}", json={"quantidade": 5})
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial_b['id']}", json={"quantidade": 3})

    # Reserva os 5 da filial A inteiros — não deve afetar a disponibilidade da filial B.
    resposta_a = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial_a["id"], 5, inicio, fim)
    )
    assert resposta_a.status_code == 201

    # A filial A está esgotada agora — reservar mais 1 ali deve falhar.
    resposta_a_excedente = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial_a["id"], 1, inicio, fim)
    )
    assert resposta_a_excedente.status_code == 409

    # Mas a filial B, independente, ainda tem seus 3 disponíveis.
    resposta_b = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial_b["id"], 3, inicio, fim)
    )
    assert resposta_b.status_code == 201


def test_contract_item_without_stock_in_filial_fails(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    outra_filial = authed_client.post("/api/filiais", json={"nome": "Filial Sem Estoque"}).json()
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque Sem Filial", filial["id"], quantidade=5)

    response = authed_client.post(
        "/api/contracts",
        json=_contract_payload(cliente["id"], equipamento["id"], outra_filial["id"], 1, inicio, fim),
    )
    assert response.status_code == 404


def test_non_overlapping_period_ignores_previous_reservation(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 3", filial["id"], quantidade=5)

    primeiro = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 5, inicio, fim)
    )
    assert primeiro.status_code == 201

    depois_inicio = fim + timedelta(days=1)
    depois_fim = depois_inicio + timedelta(days=5)
    segundo = authed_client.post(
        "/api/contracts",
        json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 5, depois_inicio, depois_fim),
    )
    assert segundo.status_code == 201


def test_stock_equipment_status_unaffected_by_activation(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 4", filial["id"], quantidade=5)

    contract = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 2, inicio, fim)
    ).json()
    response = authed_client.post(f"/api/contracts/{contract['id']}/activate")
    assert response.status_code == 200

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_stock_equipment_status_unaffected_by_baixa(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 5", filial["id"], quantidade=5)

    contract = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 2, inicio, fim)
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={"motivo": "Devolução"})
    assert response.status_code == 200
    assert response.json()["status"] == "encerrado"

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_extend_contract_conflicts_when_stock_insufficient(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 6", filial["id"], quantidade=10)

    primeiro = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 6, inicio, fim)
    ).json()
    authed_client.post(f"/api/contracts/{primeiro['id']}/activate")

    depois_inicio = fim + timedelta(days=1)
    depois_fim = depois_inicio + timedelta(days=5)
    segundo = authed_client.post(
        "/api/contracts",
        json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 6, depois_inicio, depois_fim),
    ).json()
    authed_client.post(f"/api/contracts/{segundo['id']}/activate")

    # Estender o primeiro para invadir o período do segundo estoura o estoque (6+6 > 10).
    response = authed_client.post(
        f"/api/contracts/{primeiro['id']}/extend",
        json={"nova_data_fim": (depois_fim).isoformat()},
    )
    assert response.status_code == 409


def test_extend_contract_succeeds_when_stock_sufficient(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 7", filial["id"], quantidade=10)

    primeiro = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 4, inicio, fim)
    ).json()
    authed_client.post(f"/api/contracts/{primeiro['id']}/activate")

    depois_inicio = fim + timedelta(days=1)
    depois_fim = depois_inicio + timedelta(days=5)
    segundo = authed_client.post(
        "/api/contracts",
        json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 4, depois_inicio, depois_fim),
    ).json()
    authed_client.post(f"/api/contracts/{segundo['id']}/activate")

    response = authed_client.post(
        f"/api/contracts/{primeiro['id']}/extend",
        json={"nova_data_fim": depois_fim.isoformat()},
    )
    assert response.status_code == 200


def test_reducing_estoque_below_active_reservas_conflicts(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 8", filial["id"], quantidade=10)

    contract = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 8, inicio, fim)
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 5})
    assert response.status_code == 409


def test_reducing_estoque_above_active_reservas_succeeds(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 9", filial["id"], quantidade=10)

    contract = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 3, inicio, fim)
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 5})
    assert response.status_code == 200


def test_delete_estoque_blocked_by_active_reservation(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equipamento = _create_stock_equipment(authed_client, "Categoria Estoque 10", filial["id"], quantidade=5)

    contract = authed_client.post(
        "/api/contracts", json=_contract_payload(cliente["id"], equipamento["id"], filial["id"], 2, inicio, fim)
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.delete(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}")
    assert response.status_code == 409


def test_delete_estoque_without_reservation_succeeds(authed_client, filial):
    category = authed_client.post("/api/equipment-categories", json={"nome": "Categoria Estoque 11"}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento sem reserva", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 5})

    response = authed_client.delete(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}")
    assert response.status_code == 204
    assert authed_client.get(f"/api/equipment/{equipamento['id']}").json()["estoques"] == []
