from app.utils.security import create_access_token


def _create_category(authed_client, nome="Categoria Estoque Equip"):
    return authed_client.post("/api/equipment-categories", json={"nome": nome}).json()


def _create_equipment(authed_client, nome_categoria="Categoria Estoque Equip"):
    category = _create_category(authed_client, nome_categoria)
    return authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Estoque", "categoria_id": category["id"]}
    ).json()


def _create_filial(authed_client, nome="Filial Estoque Equip"):
    return authed_client.post("/api/filiais", json={"nome": nome}).json()


def test_set_estoque_creates_row(authed_client):
    equipment = _create_equipment(authed_client, "Cat Estoque 1")
    filial = _create_filial(authed_client, "Filial Estoque 1")

    response = authed_client.put(
        f"/api/equipment/{equipment['id']}/estoque/{filial['id']}",
        json={"quantidade": 3, "valor_diario": "50.00", "valor_mensal": "900.00", "valor_hora": "10.00"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["quantidade"] == 3
    assert body["filial_id"] == filial["id"]
    assert body["valor_diario"] == "50.00"

    equipment_atualizado = authed_client.get(f"/api/equipment/{equipment['id']}").json()
    assert equipment_atualizado["quantidade_total"] == 3
    assert len(equipment_atualizado["estoques"]) == 1


def test_set_estoque_upserts_existing_row(authed_client):
    equipment = _create_equipment(authed_client, "Cat Estoque 2")
    filial = _create_filial(authed_client, "Filial Estoque 2")

    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial['id']}", json={"quantidade": 2})
    response = authed_client.put(
        f"/api/equipment/{equipment['id']}/estoque/{filial['id']}", json={"quantidade": 7}
    )
    assert response.status_code == 200
    assert response.json()["quantidade"] == 7

    equipment_atualizado = authed_client.get(f"/api/equipment/{equipment['id']}").json()
    assert len(equipment_atualizado["estoques"]) == 1
    assert equipment_atualizado["quantidade_total"] == 7


def test_equipment_can_have_stock_in_multiple_filiais(authed_client):
    equipment = _create_equipment(authed_client, "Cat Estoque 3")
    filial_a = _create_filial(authed_client, "Filial Estoque 3A")
    filial_b = _create_filial(authed_client, "Filial Estoque 3B")

    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial_a['id']}", json={"quantidade": 8})
    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial_b['id']}", json={"quantidade": 4})

    equipment_atualizado = authed_client.get(f"/api/equipment/{equipment['id']}").json()
    assert equipment_atualizado["quantidade_total"] == 12
    assert len(equipment_atualizado["estoques"]) == 2


def test_set_estoque_requires_existing_equipment(authed_client):
    filial = _create_filial(authed_client, "Filial Estoque 4")
    response = authed_client.put("/api/equipment/999999/estoque/" + str(filial["id"]), json={"quantidade": 1})
    assert response.status_code == 404


def test_set_estoque_requires_existing_filial(authed_client):
    equipment = _create_equipment(authed_client, "Cat Estoque 5")
    response = authed_client.put(f"/api/equipment/{equipment['id']}/estoque/999999", json={"quantidade": 1})
    assert response.status_code == 404


def test_delete_estoque_requires_existing_row(authed_client):
    equipment = _create_equipment(authed_client, "Cat Estoque 6")
    filial = _create_filial(authed_client, "Filial Estoque 6")
    response = authed_client.delete(f"/api/equipment/{equipment['id']}/estoque/{filial['id']}")
    assert response.status_code == 404


def test_set_estoque_requires_admin_or_operador(client, admin_user, operador_user, financeiro_user):
    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"}
    category = client.post(
        "/api/equipment-categories", json={"nome": "Cat Estoque 7"}, headers=admin_headers
    ).json()
    equipment = client.post(
        "/api/equipment",
        json={"nome": "Equipamento Estoque", "categoria_id": category["id"]},
        headers=admin_headers,
    ).json()
    filial = client.post(
        "/api/filiais", json={"nome": "Filial Estoque 7"}, headers=admin_headers
    ).json()

    financeiro_headers = {"Authorization": f"Bearer {create_access_token(subject=str(financeiro_user.id))}"}
    response = client.put(
        f"/api/equipment/{equipment['id']}/estoque/{filial['id']}",
        json={"quantidade": 1},
        headers=financeiro_headers,
    )
    assert response.status_code == 403

    operador_headers = {"Authorization": f"Bearer {create_access_token(subject=str(operador_user.id))}"}
    response = client.put(
        f"/api/equipment/{equipment['id']}/estoque/{filial['id']}",
        json={"quantidade": 1},
        headers=operador_headers,
    )
    assert response.status_code == 200


def test_list_estoque_open_to_any_role(client, admin_user, financeiro_user):
    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"}
    category = client.post(
        "/api/equipment-categories", json={"nome": "Cat Estoque 8"}, headers=admin_headers
    ).json()
    equipment = client.post(
        "/api/equipment",
        json={"nome": "Equipamento Estoque", "categoria_id": category["id"]},
        headers=admin_headers,
    ).json()
    filial = client.post("/api/filiais", json={"nome": "Filial Estoque 8"}, headers=admin_headers).json()
    client.put(
        f"/api/equipment/{equipment['id']}/estoque/{filial['id']}",
        json={"quantidade": 1},
        headers=admin_headers,
    )

    financeiro_headers = {"Authorization": f"Bearer {create_access_token(subject=str(financeiro_user.id))}"}
    response = client.get(f"/api/equipment/{equipment['id']}/estoque", headers=financeiro_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
