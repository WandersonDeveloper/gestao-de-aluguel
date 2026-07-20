def _payload(documento="11.111.111/0001-11"):
    return {
        "nome": "Fornecedor Peças LTDA",
        "documento": documento,
        "telefone": "11999999999",
        "email": "contato@fornecedor.com",
    }


def test_create_and_get_supplier(authed_client):
    response = authed_client.post("/api/suppliers", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "Fornecedor Peças LTDA"

    get_response = authed_client.get(f"/api/suppliers/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


def test_create_supplier_with_duplicate_documento_conflicts(authed_client):
    authed_client.post("/api/suppliers", json=_payload(documento="22.222.222/0001-22"))
    response = authed_client.post("/api/suppliers", json=_payload(documento="22.222.222/0001-22"))
    assert response.status_code == 409


def test_get_missing_supplier_returns_404(authed_client):
    assert authed_client.get("/api/suppliers/999999").status_code == 404


def test_update_supplier(authed_client):
    created = authed_client.post("/api/suppliers", json=_payload(documento="33.333.333/0001-33")).json()
    response = authed_client.patch(f"/api/suppliers/{created['id']}", json={"telefone": "11888888888"})
    assert response.status_code == 200
    assert response.json()["telefone"] == "11888888888"


def test_delete_supplier(authed_client):
    created = authed_client.post("/api/suppliers", json=_payload(documento="44.444.444/0001-44")).json()
    response = authed_client.delete(f"/api/suppliers/{created['id']}")
    assert response.status_code == 204
    assert authed_client.get(f"/api/suppliers/{created['id']}").status_code == 404


def test_list_suppliers_filters_by_nome(authed_client):
    authed_client.post("/api/suppliers", json=_payload(documento="55.555.555/0001-55"))
    response = authed_client.get("/api/suppliers", params={"nome": "Peças"})
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_suppliers_require_authentication(client):
    response = client.get("/api/suppliers")
    assert response.status_code == 401
