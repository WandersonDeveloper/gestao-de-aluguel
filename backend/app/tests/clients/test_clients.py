def _payload(documento="123.456.789-00"):
    return {
        "nome": "João da Silva",
        "tipo": "PF",
        "documento": documento,
        "telefone": "11999999999",
        "email": "joao@example.com",
    }


def test_create_and_get_client(authed_client):
    response = authed_client.post("/api/clients", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["nome"] == "João da Silva"
    assert body["documento"] == "123.456.789-00"

    get_response = authed_client.get(f"/api/clients/{body['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


def test_create_client_with_duplicate_documento_conflicts(authed_client):
    authed_client.post("/api/clients", json=_payload(documento="000.000.000-00"))
    response = authed_client.post("/api/clients", json=_payload(documento="000.000.000-00"))
    assert response.status_code == 409


def test_get_missing_client_returns_404(authed_client):
    response = authed_client.get("/api/clients/999999")
    assert response.status_code == 404


def test_update_client(authed_client):
    created = authed_client.post("/api/clients", json=_payload(documento="111.111.111-11")).json()
    response = authed_client.patch(f"/api/clients/{created['id']}", json={"telefone": "11888888888"})
    assert response.status_code == 200
    assert response.json()["telefone"] == "11888888888"


def test_delete_client(authed_client):
    created = authed_client.post("/api/clients", json=_payload(documento="222.222.222-22")).json()
    response = authed_client.delete(f"/api/clients/{created['id']}")
    assert response.status_code == 204
    assert authed_client.get(f"/api/clients/{created['id']}").status_code == 404


def test_list_clients_filters_by_nome(authed_client):
    authed_client.post("/api/clients", json=_payload(documento="333.333.333-33"))
    response = authed_client.get("/api/clients", params={"nome": "João"})
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_list_clients_requires_authentication(client):
    response = client.get("/api/clients")
    assert response.status_code == 401
