def _create_contract(authed_client, cliente, equipamento, filial, inicio, fim):
    return authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
    ).json()


def test_admin_can_delete_draft_contract(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.delete(f"/api/contracts/{contract['id']}")
    assert response.status_code == 204
    assert authed_client.get(f"/api/contracts/{contract['id']}").status_code == 404


def test_cannot_delete_activated_contract(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.delete(f"/api/contracts/{contract['id']}")
    assert response.status_code == 409
    assert authed_client.get(f"/api/contracts/{contract['id']}").status_code == 200


def test_delete_contract_requires_existing_contract(authed_client):
    response = authed_client.delete("/api/contracts/999999")
    assert response.status_code == 404


def test_operador_cannot_delete_contract(client, admin_user, operador_user, periodo_atual):
    from app.utils.security import create_access_token

    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"}
    inicio, fim = periodo_atual
    cliente = client.post(
        "/api/clients",
        json={"nome": "Cliente Del Op", "tipo": "PF", "documento": "666.000.111-01"},
        headers=admin_headers,
    ).json()
    filial = client.post("/api/filiais", json={"nome": "Filial Del Op"}, headers=admin_headers).json()
    category = client.post(
        "/api/equipment-categories", json={"nome": "Cat Del Op"}, headers=admin_headers
    ).json()
    equipamento = client.post(
        "/api/equipment", json={"nome": "Equip Del Op", "categoria_id": category["id"]}, headers=admin_headers
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
        },
        headers=admin_headers,
    ).json()

    operador_headers = {"Authorization": f"Bearer {create_access_token(subject=str(operador_user.id))}"}
    response = client.delete(f"/api/contracts/{contract['id']}", headers=operador_headers)
    assert response.status_code == 403


def test_financeiro_cannot_delete_contract(client, admin_user, financeiro_user, cliente, equipamento, filial, periodo_atual):
    from app.utils.security import create_access_token

    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"}
    inicio, fim = periodo_atual
    contract = client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
        headers=admin_headers,
    ).json()

    financeiro_headers = {"Authorization": f"Bearer {create_access_token(subject=str(financeiro_user.id))}"}
    response = client.delete(f"/api/contracts/{contract['id']}", headers=financeiro_headers)
    assert response.status_code == 403
