from app.config import whatsapp


def _create_contract(authed_client, cliente, equipamento, filial, inicio, fim):
    return authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "500.00",
        },
    ).json()


def test_send_contract_whatsapp_success(authed_client, equipamento, filial, periodo_atual, monkeypatch):
    calls = []
    monkeypatch.setattr(
        whatsapp,
        "send_document",
        lambda phone, base64_content, filename, caption: calls.append((phone, filename, caption)),
    )

    cliente = authed_client.post(
        "/api/clients",
        json={
            "nome": "Cliente Contrato WhatsApp",
            "tipo": "PF",
            "documento": "444.444.444-01",
            "telefone": "(11) 98888-0001",
        },
    ).json()
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.post(f"/api/contracts/{contract['id']}/send-whatsapp")
    assert response.status_code == 204
    assert len(calls) == 1
    phone, filename, _ = calls[0]
    assert phone == "(11) 98888-0001"
    assert filename == f"contrato_{contract['id']}.pdf"


def test_send_contract_whatsapp_requires_client_phone(authed_client, equipamento, filial, periodo_atual, monkeypatch):
    monkeypatch.setattr(whatsapp, "send_document", lambda *args, **kwargs: None)

    cliente = authed_client.post(
        "/api/clients",
        json={"nome": "Cliente Sem Telefone", "tipo": "PF", "documento": "444.444.444-02"},
    ).json()
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.post(f"/api/contracts/{contract['id']}/send-whatsapp")
    assert response.status_code == 409


def test_send_contract_whatsapp_requires_existing_contract(authed_client, monkeypatch):
    monkeypatch.setattr(whatsapp, "send_document", lambda *args, **kwargs: None)

    response = authed_client.post("/api/contracts/999999/send-whatsapp")
    assert response.status_code == 404
