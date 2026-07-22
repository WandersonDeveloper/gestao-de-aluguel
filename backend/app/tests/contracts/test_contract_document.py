def _create_contract(authed_client, cliente, equipamento, filial, inicio, fim, tipo="locacao"):
    return authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "500.00",
            "tipo": tipo,
        },
    ).json()


def test_contract_defaults_to_locacao(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    response = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    )
    assert response.status_code == 201
    assert response.json()["tipo"] == "locacao"


def test_generate_document_for_locacao_contract_returns_pdf(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim, tipo="locacao")

    response = authed_client.get(f"/api/contracts/{contract['id']}/documento")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_generate_document_for_servico_contract_returns_pdf(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim, tipo="servico")
    assert contract["tipo"] == "servico"

    response = authed_client.get(f"/api/contracts/{contract['id']}/documento")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content[:4] == b"%PDF"


def test_generate_document_requires_existing_contract(authed_client):
    response = authed_client.get("/api/contracts/999999/documento")
    assert response.status_code == 404


def test_generate_document_open_to_any_authenticated_role(client, admin_user, financeiro_user, periodo_atual):
    from app.utils.security import create_access_token

    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"}
    inicio, fim = periodo_atual
    cliente = client.post(
        "/api/clients",
        json={"nome": "Cliente Doc RBAC", "tipo": "PF", "documento": "888.000.111-01"},
        headers=admin_headers,
    ).json()
    filial = client.post("/api/filiais", json={"nome": "Filial Doc RBAC"}, headers=admin_headers).json()
    category = client.post(
        "/api/equipment-categories", json={"nome": "Cat Doc RBAC"}, headers=admin_headers
    ).json()
    equipamento = client.post(
        "/api/equipment", json={"nome": "Equip Doc RBAC", "categoria_id": category["id"]}, headers=admin_headers
    ).json()
    client.put(
        f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}",
        json={"quantidade": 1},
        headers=admin_headers,
    )
    contract = client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "500.00",
        },
        headers=admin_headers,
    ).json()

    financeiro_headers = {"Authorization": f"Bearer {create_access_token(subject=str(financeiro_user.id))}"}
    response = client.get(f"/api/contracts/{contract['id']}/documento", headers=financeiro_headers)
    assert response.status_code == 200
