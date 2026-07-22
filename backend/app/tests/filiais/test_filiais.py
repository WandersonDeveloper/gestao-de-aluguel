def _payload(nome="Filial Centro"):
    return {"nome": nome, "endereco": "Rua A, 100", "telefone": "11999999999"}


def test_create_and_get_filial(authed_client):
    response = authed_client.post("/api/filiais", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Filial Centro"

    get_response = authed_client.get(f"/api/filiais/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


def test_create_filial_with_duplicate_nome_conflicts(authed_client):
    authed_client.post("/api/filiais", json=_payload(nome="Filial Norte"))
    response = authed_client.post("/api/filiais", json=_payload(nome="Filial Norte"))
    assert response.status_code == 409


def test_get_missing_filial_returns_404(authed_client):
    assert authed_client.get("/api/filiais/999999").status_code == 404


def test_update_filial(authed_client):
    created = authed_client.post("/api/filiais", json=_payload(nome="Filial Sul")).json()
    response = authed_client.patch(f"/api/filiais/{created['id']}", json={"telefone": "11888888888"})
    assert response.status_code == 200
    assert response.json()["telefone"] == "11888888888"


def test_delete_filial(authed_client):
    created = authed_client.post("/api/filiais", json=_payload(nome="Filial Leste")).json()
    response = authed_client.delete(f"/api/filiais/{created['id']}")
    assert response.status_code == 204
    assert authed_client.get(f"/api/filiais/{created['id']}").status_code == 404


def test_delete_filial_with_equipment_stock_conflicts(authed_client):
    filial = authed_client.post("/api/filiais", json=_payload(nome="Filial Oeste")).json()
    categoria = authed_client.post("/api/equipment-categories", json={"nome": "Categoria Filial"}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Betoneira Filial", "categoria_id": categoria["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 1})

    response = authed_client.delete(f"/api/filiais/{filial['id']}")
    assert response.status_code == 409


def test_list_filiais_requires_authentication(client):
    assert client.get("/api/filiais").status_code == 401


def test_create_filial_requires_admin(operador_client):
    response = operador_client.post("/api/filiais", json=_payload(nome="Filial Restrita"))
    assert response.status_code == 403


def test_list_filiais_open_to_any_role(operador_client):
    response = operador_client.get("/api/filiais")
    assert response.status_code == 200
