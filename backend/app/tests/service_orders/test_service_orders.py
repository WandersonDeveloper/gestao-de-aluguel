def _create_equipment(authed_client, nome_categoria="Categoria OS"):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    return authed_client.post(
        "/api/equipment", json={"nome": "Equipamento OS", "categoria_id": category["id"]}
    ).json()


def test_create_service_order_success(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS A")
    response = authed_client.post(
        "/api/service-orders",
        json={
            "equipamento_id": equipamento["id"],
            "tipo": "corretiva",
            "descricao": "Vazamento de óleo",
            "prioridade": "alta",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "aberta"
    assert body["equipamento_id"] == equipamento["id"]


def test_create_service_order_requires_existing_equipment(authed_client):
    response = authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": 999999, "tipo": "preventiva", "descricao": "Revisão"},
    )
    assert response.status_code == 404


def test_create_service_order_requires_existing_contract_if_provided(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS B")
    response = authed_client.post(
        "/api/service-orders",
        json={
            "equipamento_id": equipamento["id"],
            "contrato_id": 999999,
            "tipo": "preventiva",
            "descricao": "Revisão",
        },
    )
    assert response.status_code == 404


def test_cannot_open_second_service_order_for_same_equipment(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS C")
    payload = {"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Revisão"}
    first = authed_client.post("/api/service-orders", json=payload)
    assert first.status_code == 201

    second = authed_client.post("/api/service-orders", json=payload)
    assert second.status_code == 409


def test_start_service_order(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS D")
    os_created = authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Revisão"},
    ).json()

    response = authed_client.post(f"/api/service-orders/{os_created['id']}/start")
    assert response.status_code == 200
    assert response.json()["status"] == "em_andamento"


def test_cannot_start_service_order_twice(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS E")
    os_created = authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Revisão"},
    ).json()
    authed_client.post(f"/api/service-orders/{os_created['id']}/start")

    response = authed_client.post(f"/api/service-orders/{os_created['id']}/start")
    assert response.status_code == 409


def test_complete_service_order_releases_equipment_if_in_maintenance(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS F")
    authed_client.post(
        f"/api/equipment/{equipamento['id']}/status", json={"status": "manutencao"}
    )
    os_created = authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "corretiva", "descricao": "Troca de peça"},
    ).json()
    authed_client.post(f"/api/service-orders/{os_created['id']}/start")

    response = authed_client.post(
        f"/api/service-orders/{os_created['id']}/complete",
        json={"observacoes": "Peça trocada com sucesso"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "concluida"

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_complete_service_order_does_not_touch_equipment_if_not_in_maintenance(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS G")
    os_created = authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Checklist"},
    ).json()
    authed_client.post(f"/api/service-orders/{os_created['id']}/start")

    response = authed_client.post(f"/api/service-orders/{os_created['id']}/complete", json={})
    assert response.status_code == 200

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_cancel_service_order_releases_equipment_if_in_maintenance(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS H")
    authed_client.post(f"/api/equipment/{equipamento['id']}/status", json={"status": "manutencao"})
    os_created = authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "corretiva", "descricao": "Diagnóstico"},
    ).json()

    response = authed_client.post(
        f"/api/service-orders/{os_created['id']}/cancel", json={"observacoes": "Aberta por engano"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelada"

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_cannot_complete_already_concluded_service_order(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS I")
    os_created = authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Checklist"},
    ).json()
    authed_client.post(f"/api/service-orders/{os_created['id']}/start")
    authed_client.post(f"/api/service-orders/{os_created['id']}/complete", json={})

    response = authed_client.post(f"/api/service-orders/{os_created['id']}/complete", json={})
    assert response.status_code == 409


def test_list_service_orders_filters_by_equipamento_and_status(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS J")
    authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Checklist"},
    )

    response = authed_client.get(
        "/api/service-orders", params={"equipamento_id": equipamento["id"], "status": "aberta"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_service_orders_require_authentication(client):
    response = client.get("/api/service-orders")
    assert response.status_code == 401


def test_delete_equipment_with_service_order_history_conflicts(authed_client):
    equipamento = _create_equipment(authed_client, "Cat OS K")
    authed_client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Checklist"},
    )

    response = authed_client.delete(f"/api/equipment/{equipamento['id']}")
    assert response.status_code == 409
