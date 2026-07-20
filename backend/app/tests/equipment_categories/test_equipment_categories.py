def test_create_and_get_category(authed_client):
    response = authed_client.post(
        "/api/equipment-categories", json={"nome": "Betoneiras", "descricao": "Mistura de concreto"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Betoneiras"

    get_response = authed_client.get(f"/api/equipment-categories/{body['id']}")
    assert get_response.status_code == 200


def test_duplicate_category_nome_conflicts(authed_client):
    authed_client.post("/api/equipment-categories", json={"nome": "Andaimes"})
    response = authed_client.post("/api/equipment-categories", json={"nome": "Andaimes"})
    assert response.status_code == 409


def test_get_missing_category_returns_404(authed_client):
    assert authed_client.get("/api/equipment-categories/999999").status_code == 404


def test_update_and_delete_category(authed_client):
    created = authed_client.post("/api/equipment-categories", json={"nome": "Caçambas"}).json()

    updated = authed_client.patch(
        f"/api/equipment-categories/{created['id']}", json={"descricao": "Para entulho"}
    )
    assert updated.status_code == 200
    assert updated.json()["descricao"] == "Para entulho"

    deleted = authed_client.delete(f"/api/equipment-categories/{created['id']}")
    assert deleted.status_code == 204
    assert authed_client.get(f"/api/equipment-categories/{created['id']}").status_code == 404


def test_list_categories_requires_authentication(client):
    response = client.get("/api/equipment-categories")
    assert response.status_code == 401


def test_delete_category_with_equipment_conflicts(authed_client):
    category = authed_client.post("/api/equipment-categories", json={"nome": "Escavadeiras"}).json()
    authed_client.post(
        "/api/equipment", json={"nome": "Escavadeira 320", "categoria_id": category["id"]}
    )

    response = authed_client.delete(f"/api/equipment-categories/{category['id']}")
    assert response.status_code == 409
