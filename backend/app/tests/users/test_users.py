def test_get_me_returns_current_user(authed_client, admin_user):
    response = authed_client.get("/api/users/me")
    assert response.status_code == 200
    assert response.json()["email"] == admin_user.email


def test_admin_can_create_user(authed_client):
    response = authed_client.post(
        "/api/users",
        json={
            "nome": "Novo Operador",
            "email": "novo.operador@example.com",
            "papel": "operador",
            "senha": "outrasenha123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "novo.operador@example.com"
    assert "senha" not in body
    assert "senha_hash" not in body


def test_create_user_with_duplicate_email_conflicts(authed_client, admin_user):
    response = authed_client.post(
        "/api/users",
        json={
            "nome": "Duplicado",
            "email": admin_user.email,
            "papel": "operador",
            "senha": "outrasenha123",
        },
    )
    assert response.status_code == 409


def test_non_admin_cannot_create_user(operador_client):
    response = operador_client.post(
        "/api/users",
        json={
            "nome": "Tentativa",
            "email": "tentativa@example.com",
            "papel": "operador",
            "senha": "outrasenha123",
        },
    )
    assert response.status_code == 403


def test_non_admin_cannot_list_users(operador_client):
    response = operador_client.get("/api/users")
    assert response.status_code == 403
