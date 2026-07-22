from app.config import whatsapp
from app.config.settings import settings

WEBHOOK_URL = f"/api/webhooks/whatsapp/{settings.whatsapp_webhook_secret}"


def _create_client(authed_client, documento, telefone):
    return authed_client.post(
        "/api/clients",
        json={"nome": "Cliente Aditivo", "tipo": "PF", "documento": documento, "telefone": telefone},
    ).json()


def _create_active_contract(authed_client, cliente, equipamento, filial, inicio, fim):
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    return contract


def _create_second_equipment(authed_client, filial):
    category = authed_client.post("/api/equipment-categories", json={"nome": "Cat Aditivo Webhook"}).json()
    equipment = authed_client.post(
        "/api/equipment", json={"nome": "Andaime Extra Webhook", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial['id']}", json={"quantidade": 5})
    return equipment


def _webhook_payload(texto: str, remote_jid: str) -> dict:
    return {
        "event": "messages.upsert",
        "data": {"key": {"remoteJid": remote_jid, "fromMe": False, "id": "ABC123"}, "message": {"conversation": texto}},
    }


def test_add_items_sends_confirmation_and_marks_amendment_aguardando(
    authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    monkeypatch.setattr(whatsapp, "send_text", lambda *a, **kw: None)
    cliente = _create_client(authed_client, "555.222.111-01", "(69) 98888-0001")
    inicio, fim = periodo_atual
    contract = _create_active_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    novo_equipamento = _create_second_equipment(authed_client, filial)
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 200

    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    aditivo = next(a for a in amendments if a["tipo"] == "adicao_item")
    assert aditivo["assinatura_status"] == "aguardando_confirmacao"


def test_webhook_option_1_confirms_amendment_and_generates_comprovante(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    monkeypatch.setattr(whatsapp, "send_text", lambda *a, **kw: None)
    cliente = _create_client(authed_client, "555.222.111-02", "(69) 98888-0002")
    inicio, fim = periodo_atual
    contract = _create_active_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    novo_equipamento = _create_second_equipment(authed_client, filial)
    authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    aditivo = next(a for a in amendments if a["tipo"] == "adicao_item")

    telefone_normalizado = whatsapp.normalize_phone_br("(69) 98888-0002")
    response = client.post(WEBHOOK_URL, json=_webhook_payload("1", f"{telefone_normalizado}@s.whatsapp.net"))
    assert response.status_code == 200

    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    aditivo_atualizado = next(a for a in amendments if a["id"] == aditivo["id"])
    assert aditivo_atualizado["assinatura_status"] == "confirmado"

    comprovante = authed_client.get(
        f"/api/contracts/{contract['id']}/amendments/{aditivo['id']}/comprovante-assinatura"
    )
    assert comprovante.status_code == 200
    assert comprovante.headers["content-type"] == "application/pdf"
    assert comprovante.content[:4] == b"%PDF"

    # Confirmar o aditivo não mexe no assinatura_status do contrato em si.
    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "nao_enviado"


def test_webhook_option_2_rejects_amendment_without_reverting_item(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    monkeypatch.setattr(whatsapp, "send_text", lambda *a, **kw: None)
    cliente = _create_client(authed_client, "555.222.111-03", "(69) 98888-0003")
    inicio, fim = periodo_atual
    contract = _create_active_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    novo_equipamento = _create_second_equipment(authed_client, filial)
    authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )

    telefone_normalizado = whatsapp.normalize_phone_br("(69) 98888-0003")
    response = client.post(WEBHOOK_URL, json=_webhook_payload("2", f"{telefone_normalizado}@s.whatsapp.net"))
    assert response.status_code == 200

    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    aditivo = next(a for a in amendments if a["tipo"] == "adicao_item")
    assert aditivo["assinatura_status"] == "recusado"

    # Item continua no contrato (recusa não desfaz nada automaticamente — ver
    # contract_signature_service.recusar_aditivo).
    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert any(item["equipamento_id"] == novo_equipamento["id"] for item in detail["itens"])


def test_webhook_resolves_amendment_over_older_contract_signature_for_same_phone(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    """Se o mesmo telefone tiver o contrato original E um aditivo pendentes ao
    mesmo tempo, o webhook decide pelo mais recente — ver
    contract_signature_service._encontrar_pendente."""
    monkeypatch.setattr(whatsapp, "send_document", lambda *a, **kw: None)
    monkeypatch.setattr(whatsapp, "send_text", lambda *a, **kw: None)
    cliente = _create_client(authed_client, "555.222.111-04", "(69) 98888-0004")
    inicio, fim = periodo_atual
    contract = _create_active_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    # Contrato original ainda aguardando confirmação (send-whatsapp).
    authed_client.post(f"/api/contracts/{contract['id']}/send-whatsapp")

    # Aditivo enviado depois — deve "ganhar" por ser mais recente.
    novo_equipamento = _create_second_equipment(authed_client, filial)
    authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )

    telefone_normalizado = whatsapp.normalize_phone_br("(69) 98888-0004")
    response = client.post(WEBHOOK_URL, json=_webhook_payload("1", f"{telefone_normalizado}@s.whatsapp.net"))
    assert response.status_code == 200

    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "aguardando_confirmacao"  # contrato original não mexido

    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    aditivo = next(a for a in amendments if a["tipo"] == "adicao_item")
    assert aditivo["assinatura_status"] == "confirmado"
