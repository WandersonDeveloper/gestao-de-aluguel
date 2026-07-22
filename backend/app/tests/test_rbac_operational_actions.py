from datetime import date, timedelta

from app.utils.security import create_access_token


def _headers(user) -> dict:
    return {"Authorization": f"Bearer {create_access_token(subject=str(user.id))}"}


def _setup_cliente_e_equipamento(client, admin_user, sufixo: str):
    admin_headers = _headers(admin_user)
    cliente = client.post(
        "/api/clients",
        json={"nome": f"Cliente RBAC {sufixo}", "tipo": "PF", "documento": f"{sufixo}-000.000-00"},
        headers=admin_headers,
    ).json()
    filial = client.post("/api/filiais", json={"nome": f"Filial RBAC {sufixo}"}, headers=admin_headers).json()
    category = client.post(
        "/api/equipment-categories", json={"nome": f"Cat RBAC {sufixo}"}, headers=admin_headers
    ).json()
    equipamento = client.post(
        "/api/equipment",
        json={"nome": f"Equip RBAC {sufixo}", "categoria_id": category["id"]},
        headers=admin_headers,
    ).json()
    client.put(
        f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}",
        json={"quantidade": 1},
        headers=admin_headers,
    )
    return cliente, equipamento, filial


def test_financeiro_cannot_create_contract(client, admin_user, financeiro_user):
    cliente, equipamento, filial = _setup_cliente_e_equipamento(client, admin_user, "1")
    inicio = date.today()
    fim = inicio + timedelta(days=5)

    response = client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
        headers=_headers(financeiro_user),
    )
    assert response.status_code == 403


def test_operador_can_create_contract(client, admin_user, operador_user):
    cliente, equipamento, filial = _setup_cliente_e_equipamento(client, admin_user, "2")
    inicio = date.today()
    fim = inicio + timedelta(days=5)

    response = client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
        },
        headers=_headers(operador_user),
    )
    assert response.status_code == 201


def test_financeiro_cannot_change_equipment_status(client, admin_user, financeiro_user):
    _, equipamento, _ = _setup_cliente_e_equipamento(client, admin_user, "3")

    response = client.post(
        f"/api/equipment/{equipamento['id']}/status",
        json={"status": "manutencao"},
        headers=_headers(financeiro_user),
    )
    assert response.status_code == 403


def test_financeiro_cannot_create_service_order(client, admin_user, financeiro_user):
    _, equipamento, _ = _setup_cliente_e_equipamento(client, admin_user, "4")

    response = client.post(
        "/api/service-orders",
        json={"equipamento_id": equipamento["id"], "tipo": "preventiva", "descricao": "Revisão"},
        headers=_headers(financeiro_user),
    )
    assert response.status_code == 403


def test_financeiro_can_still_read_contracts(client, financeiro_user):
    response = client.get("/api/contracts", headers=_headers(financeiro_user))
    assert response.status_code == 200
