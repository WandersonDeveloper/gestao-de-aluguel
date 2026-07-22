from datetime import date, timedelta
from decimal import Decimal

from app.services import invoice_service


def _create_and_activate_overdue_contract(authed_client, documento, nome_categoria, valor_total="1000.00"):
    cliente = authed_client.post(
        "/api/clients", json={"nome": "Cliente Atraso", "tipo": "PF", "documento": documento}
    ).json()
    filial = authed_client.post("/api/filiais", json={"nome": f"Filial {nome_categoria}"}).json()
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Atraso", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 1})
    inicio = date.today() - timedelta(days=10)
    fim = date.today() - timedelta(days=5)
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


def test_mark_overdue_invoices_applies_late_fee(authed_client, db_session):
    _, invoice = _create_and_activate_overdue_contract(authed_client, "333.333.333-01", "Cat Atraso A")
    assert invoice["status"] == "pendente"

    faturas = invoice_service.mark_overdue_invoices(db_session)

    assert any(f.id == invoice["id"] for f in faturas)
    atualizada = next(f for f in faturas if f.id == invoice["id"])
    assert atualizada.status.value == "atrasada"
    assert atualizada.multa_juros_aplicado == Decimal("20.00")  # 2% de 1000.00


def test_mark_overdue_invoices_does_not_touch_future_invoice(authed_client, db_session):
    cliente = authed_client.post(
        "/api/clients", json={"nome": "Cliente Futuro", "tipo": "PF", "documento": "333.333.333-02"}
    ).json()
    filial = authed_client.post("/api/filiais", json={"nome": "Filial Cat Atraso B"}).json()
    category = authed_client.post("/api/equipment-categories", json={"nome": "Cat Atraso B"}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Futuro", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento['id']}/estoque/{filial['id']}", json={"quantidade": 1})
    inicio = date.today() + timedelta(days=5)
    fim = inicio + timedelta(days=5)
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "100.00",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    invoice = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()[0]

    faturas = invoice_service.mark_overdue_invoices(db_session)

    assert not any(f.id == invoice["id"] for f in faturas)
