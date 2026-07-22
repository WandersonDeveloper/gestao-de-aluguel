import httpx

from app.config import whatsapp
from app.config.settings import settings


class _FakeResponse:
    status_code = 201
    content = b"{}"

    def raise_for_status(self):
        pass

    def json(self):
        return {}


def test_create_instance_uses_baileys_qrcode_by_default(monkeypatch):
    monkeypatch.setattr(settings, "meta_whatsapp_token", "")
    monkeypatch.setattr(settings, "meta_whatsapp_number_id", "")

    captured = {}

    def fake_request(method, url, json=None, **kwargs):
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    whatsapp.create_instance()
    assert captured["json"]["integration"] == "WHATSAPP-BAILEYS"
    assert captured["json"]["qrcode"] is True
    assert "token" not in captured["json"]


def test_create_instance_uses_official_business_api_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "meta_whatsapp_token", "token-permanente")
    monkeypatch.setattr(settings, "meta_whatsapp_number_id", "123456")
    monkeypatch.setattr(settings, "meta_whatsapp_business_id", "789")

    captured = {}

    def fake_request(method, url, json=None, **kwargs):
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    whatsapp.create_instance()
    assert captured["json"]["integration"] == "WHATSAPP-BUSINESS"
    assert captured["json"]["qrcode"] is False
    assert captured["json"]["token"] == "token-permanente"
    assert captured["json"]["number"] == "123456"
    assert captured["json"]["businessId"] == "789"


def test_set_webhook_sends_expected_payload(monkeypatch):
    captured = {}

    def fake_request(method, url, json=None, **kwargs):
        captured["method"] = method
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse()

    monkeypatch.setattr(httpx, "request", fake_request)

    whatsapp.set_webhook("http://backend:8000/api/webhooks/whatsapp/segredo", ["MESSAGES_UPSERT"])

    assert captured["method"] == "POST"
    assert captured["url"].endswith(f"/webhook/set/{settings.evolution_instance_name}")
    assert captured["json"] == {
        "webhook": {
            "url": "http://backend:8000/api/webhooks/whatsapp/segredo",
            "enabled": True,
            "webhookByEvents": False,
            "events": ["MESSAGES_UPSERT"],
        }
    }
