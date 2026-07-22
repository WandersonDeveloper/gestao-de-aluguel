from datetime import date, timedelta

from app.utils.security import create_access_token


def _create_and_activate_contract(authed_client, documento, nome_categoria, valor_total="500.00"):
    cliente = authed_client.post(
        "/api/clients", json={"nome": "Cliente Pagamento", "tipo": "PF", "documento": documento}
    ).json()
    filial = authed_client.post("/api/filiais", json={"nome": f"Filial {nome_categoria}"}).json()
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Pagamento", "categoria_id": category["id"]}
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
            "valor_total": valor_total,
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    invoice = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()[0]
    return contract, invoice


def test_full_payment_marks_invoice_as_paid(authed_client):
    _, invoice = _create_and_activate_contract(authed_client, "222.222.222-01", "Cat Pag A")

    response = authed_client.post(
        f"/api/invoices/{invoice['id']}/payments", json={"valor": "500.00", "forma_pagamento": "pix"}
    )
    assert response.status_code == 201

    updated = authed_client.get(f"/api/invoices/{invoice['id']}").json()
    assert updated["status"] == "paga"


def test_partial_payment_keeps_invoice_pending(authed_client):
    _, invoice = _create_and_activate_contract(authed_client, "222.222.222-02", "Cat Pag B")

    authed_client.post(f"/api/invoices/{invoice['id']}/payments", json={"valor": "200.00"})

    updated = authed_client.get(f"/api/invoices/{invoice['id']}").json()
    assert updated["status"] == "pendente"


def test_two_partial_payments_sum_to_full_marks_paid(authed_client):
    _, invoice = _create_and_activate_contract(authed_client, "222.222.222-03", "Cat Pag C")

    authed_client.post(f"/api/invoices/{invoice['id']}/payments", json={"valor": "300.00"})
    authed_client.post(f"/api/invoices/{invoice['id']}/payments", json={"valor": "200.00"})

    updated = authed_client.get(f"/api/invoices/{invoice['id']}").json()
    assert updated["status"] == "paga"

    payments = authed_client.get(f"/api/invoices/{invoice['id']}/payments").json()
    assert len(payments) == 2


def test_cannot_pay_cancelled_invoice(authed_client):
    _, invoice = _create_and_activate_contract(authed_client, "222.222.222-04", "Cat Pag D")
    authed_client.post(f"/api/invoices/{invoice['id']}/cancel")

    response = authed_client.post(f"/api/invoices/{invoice['id']}/payments", json={"valor": "100.00"})
    assert response.status_code == 409


def test_negative_payment_rejected(authed_client):
    _, invoice = _create_and_activate_contract(authed_client, "222.222.222-05", "Cat Pag E")

    response = authed_client.post(f"/api/invoices/{invoice['id']}/payments", json={"valor": "-10.00"})
    assert response.status_code == 409


def test_operador_cannot_register_payment(client, admin_user, operador_user):
    admin_headers = {"Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"}
    cliente = client.post(
        "/api/clients",
        json={"nome": "Cliente RBAC Pag", "tipo": "PF", "documento": "222.222.222-06"},
        headers=admin_headers,
    ).json()
    filial = client.post("/api/filiais", json={"nome": "Filial Pag RBAC"}, headers=admin_headers).json()
    category = client.post(
        "/api/equipment-categories", json={"nome": "Cat Pag RBAC"}, headers=admin_headers
    ).json()
    equipamento = client.post(
        "/api/equipment",
        json={"nome": "Equip Pag RBAC", "categoria_id": category["id"]},
        headers=admin_headers,
    ).json()
    client.put(
        f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}",
        json={"quantidade": 1},
        headers=admin_headers,
    )
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    contract = client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "100.00",
        },
        headers=admin_headers,
    ).json()
    client.post(f"/api/contracts/{contract['id']}/activate", headers=admin_headers)
    invoice = client.get(
        "/api/invoices", params={"contrato_id": contract["id"]}, headers=admin_headers
    ).json()[0]

    operador_headers = {"Authorization": f"Bearer {create_access_token(subject=str(operador_user.id))}"}
    response = client.post(
        f"/api/invoices/{invoice['id']}/payments", json={"valor": "100.00"}, headers=operador_headers
    )
    assert response.status_code == 403


def test_invoices_require_authentication(client):
    response = client.get("/api/invoices")
    assert response.status_code == 401
