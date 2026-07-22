from app.config import whatsapp
from app.config.settings import settings

WEBHOOK_URL = f"/api/webhooks/whatsapp/{settings.whatsapp_webhook_secret}"


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


def _send_contract_via_whatsapp(authed_client, equipamento, filial, periodo_atual, monkeypatch, documento, telefone):
    monkeypatch.setattr(whatsapp, "send_document", lambda *args, **kwargs: None)
    monkeypatch.setattr(whatsapp, "send_text", lambda *args, **kwargs: None)
    cliente = authed_client.post(
        "/api/clients",
        json={"nome": "Cliente Assinatura", "tipo": "PF", "documento": documento, "telefone": telefone},
    ).json()
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/send-whatsapp")
    return contract, cliente


def _webhook_payload(texto: str, remote_jid: str, from_me: bool = False, sender_pn: str | None = None) -> dict:
    key: dict = {"remoteJid": remote_jid, "fromMe": from_me, "id": "ABC123"}
    if sender_pn:
        # Confirmado ao vivo: a Evolution API manda `senderPn` DENTRO de
        # `key`, não como irmão de `key` em `data` — um payload de teste
        # anterior modelava isso errado e mascarava um bug real (ver
        # contract_signature_service._extrair_telefone).
        key["senderPn"] = sender_pn
    data = {
        "key": key,
        "pushName": "Cliente",
        "message": {"conversation": texto},
    }
    return {"event": "messages.upsert", "data": data}


def test_send_contract_whatsapp_marks_aguardando_confirmacao(
    authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    contract, _ = _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-01", "(69) 99999-0001"
    )

    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "aguardando_confirmacao"


def test_webhook_option_1_confirms_contract_and_generates_comprovante(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    contract, _ = _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-02", "(69) 99999-0002"
    )
    telefone_normalizado = whatsapp.normalize_phone_br("(69) 99999-0002")

    response = client.post(
        WEBHOOK_URL,
        json=_webhook_payload("1", f"{telefone_normalizado}@s.whatsapp.net"),
    )
    assert response.status_code == 200

    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "confirmado"
    assert detail["assinatura_resposta_texto"] == "1"

    comprovante = authed_client.get(f"/api/contracts/{contract['id']}/comprovante-assinatura")
    assert comprovante.status_code == 200
    assert comprovante.headers["content-type"] == "application/pdf"
    assert comprovante.content[:4] == b"%PDF"


def test_webhook_option_2_rejects_contract(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    contract, _ = _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-06", "(69) 99999-0006"
    )
    telefone_normalizado = whatsapp.normalize_phone_br("(69) 99999-0006")

    response = client.post(
        WEBHOOK_URL,
        json=_webhook_payload("2", f"{telefone_normalizado}@s.whatsapp.net"),
    )
    assert response.status_code == 200

    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "recusado"
    assert detail["assinatura_resposta_texto"] == "2"

    comprovante = authed_client.get(f"/api/contracts/{contract['id']}/comprovante-assinatura")
    assert comprovante.status_code == 404


def test_webhook_confirms_using_senderpn_when_remotejid_is_lid(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    """A Evolution API às vezes manda key.remoteJid no formato "@lid" (linked
    ID), que não é o número de telefone — o número real vem em `senderPn`.
    Confirmado ao vivo contra a instância real (ver regras-de-negocio.md)."""
    contract, _ = _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-05", "(69) 99999-0005"
    )
    telefone_normalizado = whatsapp.normalize_phone_br("(69) 99999-0005")

    response = client.post(
        WEBHOOK_URL,
        json=_webhook_payload(
            "1",
            remote_jid="119005423624412@lid",
            sender_pn=f"{telefone_normalizado}@s.whatsapp.net",
        ),
    )
    assert response.status_code == 200

    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "confirmado"


def test_webhook_rejects_wrong_secret(client):
    response = client.post(
        "/api/webhooks/whatsapp/secret-errado",
        json=_webhook_payload("1", "5511999999999@s.whatsapp.net"),
    )
    assert response.status_code == 404


def test_webhook_ignores_messages_from_me(client, authed_client, equipamento, filial, periodo_atual, monkeypatch):
    contract, _ = _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-03", "(69) 99999-0003"
    )
    telefone_normalizado = whatsapp.normalize_phone_br("(69) 99999-0003")

    response = client.post(
        WEBHOOK_URL,
        json=_webhook_payload("1", f"{telefone_normalizado}@s.whatsapp.net", from_me=True),
    )
    assert response.status_code == 200

    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "aguardando_confirmacao"


def test_webhook_ignores_reply_from_wrong_phone(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-04", "(69) 99999-0004"
    )

    response = client.post(
        WEBHOOK_URL,
        json=_webhook_payload("1", "5599999999999@s.whatsapp.net"),
    )
    assert response.status_code == 200


def test_webhook_ignores_text_that_is_not_1_or_2(
    client, authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    contract, _ = _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-07", "(69) 99999-0007"
    )
    telefone_normalizado = whatsapp.normalize_phone_br("(69) 99999-0007")

    response = client.post(
        WEBHOOK_URL,
        json=_webhook_payload("oi, tudo bem?", f"{telefone_normalizado}@s.whatsapp.net"),
    )
    assert response.status_code == 200

    detail = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert detail["assinatura_status"] == "aguardando_confirmacao"


def test_webhook_ignores_when_no_contract_pending_for_phone(client):
    response = client.post(
        WEBHOOK_URL,
        json=_webhook_payload("1", "5511999999999@s.whatsapp.net"),
    )
    assert response.status_code == 200


def test_list_contracts_filters_by_assinatura_status(
    authed_client, equipamento, filial, periodo_atual, monkeypatch
):
    contract, _ = _send_contract_via_whatsapp(
        authed_client, equipamento, filial, periodo_atual, monkeypatch, "555.111.111-08", "(69) 99999-0008"
    )

    aguardando = authed_client.get(
        "/api/contracts", params={"assinatura_status": "aguardando_confirmacao"}
    ).json()
    assert any(c["id"] == contract["id"] for c in aguardando)

    confirmados = authed_client.get("/api/contracts", params={"assinatura_status": "confirmado"}).json()
    assert not any(c["id"] == contract["id"] for c in confirmados)
