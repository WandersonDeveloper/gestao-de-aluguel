def _create_category(client, nome="Máquinas pesadas"):
    return client.post("/api/equipment-categories", json={"nome": nome}).json()


def test_create_equipment_requires_existing_category(authed_client):
    response = authed_client.post(
        "/api/equipment",
        json={"nome": "Escavadeira", "categoria_id": 999999},
    )
    assert response.status_code == 404


def test_create_and_get_equipment(authed_client):
    category = _create_category(authed_client)
    response = authed_client.post(
        "/api/equipment",
        json={
            "nome": "Escavadeira CAT 320",
            "categoria_id": category["id"],
            "identificador": "CHASSI-001",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "disponivel"
    assert body["categoria_id"] == category["id"]
    assert body["quantidade_total"] == 0
    assert body["estoques"] == []

    get_response = authed_client.get(f"/api/equipment/{body['id']}")
    assert get_response.status_code == 200


def test_duplicate_identificador_conflicts(authed_client):
    category = _create_category(authed_client, nome="Betoneiras")
    payload = {"nome": "Betoneira 400L", "categoria_id": category["id"], "identificador": "DUP-001"}
    authed_client.post("/api/equipment", json=payload)
    response = authed_client.post("/api/equipment", json=payload)
    assert response.status_code == 409


def test_patch_does_not_accept_status_field(authed_client):
    category = _create_category(authed_client, nome="Andaimes")
    created = authed_client.post(
        "/api/equipment", json={"nome": "Andaime 2m", "categoria_id": category["id"]}
    ).json()

    response = authed_client.patch(f"/api/equipment/{created['id']}", json={"status": "manutencao"})
    assert response.status_code == 200
    assert response.json()["status"] == "disponivel"


def test_list_equipment_filters_by_categoria_and_status(authed_client):
    category = _create_category(authed_client, nome="Containers")
    authed_client.post(
        "/api/equipment", json={"nome": "Container 20 pés", "categoria_id": category["id"]}
    )

    response = authed_client.get(
        "/api/equipment", params={"categoria_id": category["id"], "status": "disponivel"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_list_equipment_requires_authentication(client):
    response = client.get("/api/equipment")
    assert response.status_code == 401


def test_delete_equipment_without_history_succeeds(authed_client):
    category = _create_category(authed_client, nome="Ferramentas")
    created = authed_client.post(
        "/api/equipment", json={"nome": "Furadeira", "categoria_id": category["id"]}
    ).json()

    response = authed_client.delete(f"/api/equipment/{created['id']}")
    assert response.status_code == 204
    assert authed_client.get(f"/api/equipment/{created['id']}").status_code == 404


def test_delete_equipment_with_history_conflicts(authed_client):
    category = _create_category(authed_client, nome="Geradores")
    created = authed_client.post(
        "/api/equipment", json={"nome": "Gerador 5kva", "categoria_id": category["id"]}
    ).json()
    authed_client.post(f"/api/equipment/{created['id']}/status", json={"status": "manutencao"})

    response = authed_client.delete(f"/api/equipment/{created['id']}")
    assert response.status_code == 409
