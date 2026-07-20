def test_login_with_correct_credentials_returns_token(client, admin_user):
    response = client.post(
        "/api/auth/login", json={"email": admin_user.email, "senha": "senha123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_with_wrong_password_is_unauthorized(client, admin_user):
    response = client.post(
        "/api/auth/login", json={"email": admin_user.email, "senha": "senha-errada"}
    )
    assert response.status_code == 401


def test_login_with_unknown_email_is_unauthorized(client):
    response = client.post(
        "/api/auth/login", json={"email": "ninguem@example.com", "senha": "qualquer"}
    )
    assert response.status_code == 401


def test_request_without_token_is_unauthorized(client):
    response = client.get("/api/users/me")
    assert response.status_code == 401


def test_request_with_invalid_token_is_unauthorized(client):
    client.headers.update({"Authorization": "Bearer token-invalido"})
    response = client.get("/api/users/me")
    assert response.status_code == 401
