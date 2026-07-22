from datetime import date, timedelta

from app.config import whatsapp


def _create_and_activate_contract(authed_client, documento, nome_categoria, telefone=None):
    cliente = authed_client.post(
        "/api/clients",
        json={"nome": "Cliente WhatsApp", "tipo": "PF", "documento": documento, "telefone": telefone},
    ).json()
    filial = authed_client.post("/api/filiais", json={"nome": f"Filial {nome_categoria}"}).json()
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento WhatsApp", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 1})
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "500.00",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    invoice = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()[0]
    return contract, invoice


def test_send_invoice_whatsapp_success(authed_client, monkeypatch):
    calls = []
    monkeypatch.setattr(whatsapp, "send_text", lambda phone, message: calls.append((phone, message)))

    _, invoice = _create_and_activate_contract(
        authed_client, "333.333.333-01", "Cat WA A", telefone="(11) 99999-0001"
    )

    response = authed_client.post(f"/api/invoices/{invoice['id']}/send-whatsapp")
    assert response.status_code == 204
    assert len(calls) == 1
    phone, message = calls[0]
    assert phone == "(11) 99999-0001"
    assert "R$ 500,00" in message


def test_send_invoice_whatsapp_requires_client_phone(authed_client, monkeypatch):
    monkeypatch.setattr(whatsapp, "send_text", lambda phone, message: None)

    _, invoice = _create_and_activate_contract(authed_client, "333.333.333-02", "Cat WA B", telefone=None)

    response = authed_client.post(f"/api/invoices/{invoice['id']}/send-whatsapp")
    assert response.status_code == 409


def test_send_invoice_whatsapp_requires_existing_invoice(authed_client, monkeypatch):
    monkeypatch.setattr(whatsapp, "send_text", lambda phone, message: None)

    response = authed_client.post("/api/invoices/999999/send-whatsapp")
    assert response.status_code == 404
