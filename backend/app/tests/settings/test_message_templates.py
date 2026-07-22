from app.utils.security import create_access_token


def test_list_message_templates_returns_seeded_defaults(authed_client):
    response = authed_client.get("/api/settings/message-templates")
    assert response.status_code == 200
    chaves = {item["chave"] for item in response.json()}
    assert chaves == {
        "cobranca_fatura",
        "contrato_assinatura",
        "aceite_confirmado",
        "aceite_recusado",
        "aditivo_confirmacao",
        "aditivo_aceite_confirmado",
        "aditivo_aceite_recusado",
    }


def test_update_message_template_success(authed_client):
    response = authed_client.put(
        "/api/settings/message-templates/cobranca_fatura",
        json={"conteudo": "Oi {cliente_nome}, sua fatura de {valor} vence em {vencimento}.{multa_texto} {situacao}"},
    )
    assert response.status_code == 200
    assert response.json()["conteudo"].startswith("Oi {cliente_nome}")


def test_update_message_template_rejects_unknown_placeholder(authed_client):
    response = authed_client.put(
        "/api/settings/message-templates/cobranca_fatura",
        json={"conteudo": "Oi {cliente_nome}, seu {campo_que_nao_existe}"},
    )
    assert response.status_code == 409


def test_update_message_template_requires_admin(client, operador_user):
    headers = {"Authorization": f"Bearer {create_access_token(subject=str(operador_user.id))}"}
    response = client.put(
        "/api/settings/message-templates/cobranca_fatura",
        json={"conteudo": "qualquer coisa sem placeholder"},
        headers=headers,
    )
    assert response.status_code == 403


def test_list_message_templates_requires_admin(client, financeiro_user):
    headers = {"Authorization": f"Bearer {create_access_token(subject=str(financeiro_user.id))}"}
    response = client.get("/api/settings/message-templates", headers=headers)
    assert response.status_code == 403
