from app.config import whatsapp
from app.utils.security import create_access_token


def test_status_when_instance_does_not_exist(authed_client, monkeypatch):
    monkeypatch.setattr(whatsapp, "get_connection_state", lambda: None)

    response = authed_client.get("/api/settings/whatsapp/status")
    assert response.status_code == 200
    assert response.json() == {"existe": False, "estado": None}


def test_status_when_instance_connecting(authed_client, monkeypatch):
    monkeypatch.setattr(
        whatsapp, "get_connection_state", lambda: {"instance": {"state": "connecting"}}
    )

    response = authed_client.get("/api/settings/whatsapp/status")
    assert response.status_code == 200
    assert response.json() == {"existe": True, "estado": "connecting"}


def test_connect_creates_instance_when_missing(authed_client, monkeypatch):
    monkeypatch.setattr(whatsapp, "get_connection_state", lambda: None)
    monkeypatch.setattr(
        whatsapp,
        "create_instance",
        lambda: {"instance": {"status": "connecting"}, "qrcode": {"base64": "data:image/png;base64,AAA"}},
    )
    webhook_calls = []
    monkeypatch.setattr(whatsapp, "set_webhook", lambda url, events: webhook_calls.append((url, events)))

    response = authed_client.post("/api/settings/whatsapp/connect")
    assert response.status_code == 200
    assert response.json() == {"estado": "connecting", "qrcode_base64": "data:image/png;base64,AAA"}
    assert len(webhook_calls) == 1


def test_connect_fetches_new_qrcode_when_existing(authed_client, monkeypatch):
    monkeypatch.setattr(
        whatsapp, "get_connection_state", lambda: {"instance": {"state": "connecting"}}
    )
    monkeypatch.setattr(whatsapp, "fetch_qrcode", lambda: {"base64": "data:image/png;base64,BBB"})
    monkeypatch.setattr(whatsapp, "set_webhook", lambda url, events: None)

    response = authed_client.post("/api/settings/whatsapp/connect")
    assert response.status_code == 200
    assert response.json() == {"estado": "connecting", "qrcode_base64": "data:image/png;base64,BBB"}


def test_disconnect_calls_logout(authed_client, monkeypatch):
    calls = []
    monkeypatch.setattr(whatsapp, "logout_instance", lambda: calls.append(True))

    response = authed_client.post("/api/settings/whatsapp/disconnect")
    assert response.status_code == 204
    assert calls == [True]


def test_whatsapp_status_requires_admin(client, operador_user, monkeypatch):
    monkeypatch.setattr(whatsapp, "get_connection_state", lambda: None)
    headers = {"Authorization": f"Bearer {create_access_token(subject=str(operador_user.id))}"}

    response = client.get("/api/settings/whatsapp/status", headers=headers)
    assert response.status_code == 403
