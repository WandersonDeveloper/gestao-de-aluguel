from datetime import date, timedelta

from app.services import invoice_service


def _create_and_activate_contract(authed_client, documento, nome_categoria, valor_total="100.00", dias_passado=0):
    cliente = authed_client.post(
        "/api/clients", json={"nome": "Cliente Relatorio", "tipo": "PF", "documento": documento}
    ).json()
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipamento = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Relatorio", "categoria_id": category["id"]}
    ).json()
    inicio = date.today() - timedelta(days=dias_passado + 5)
    fim = date.today() - timedelta(days=dias_passado)
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "equipamento_ids": [equipamento["id"]],
            "valor_total": valor_total,
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    return contract, equipamento


def test_dashboard_report_returns_counts(authed_client):
    _create_and_activate_contract(authed_client, "444.444.444-01", "Cat Relatorio A", dias_passado=10)

    response = authed_client.get("/api/reports/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["equipamentos_total"] >= 1
    assert "faturas_atrasadas_valor_total" in body


def test_most_rented_equipment_report(authed_client):
    _, equipamento = _create_and_activate_contract(authed_client, "444.444.444-02", "Cat Relatorio B", dias_passado=10)

    response = authed_client.get("/api/reports/most-rented-equipment")
    assert response.status_code == 200
    nomes = [entry["equipamento_id"] for entry in response.json()]
    assert equipamento["id"] in nomes


def test_overdue_invoices_report_groups_by_client(authed_client, db_session):
    contract, _ = _create_and_activate_contract(
        authed_client, "444.444.444-03", "Cat Relatorio C", valor_total="1000.00", dias_passado=10
    )
    invoice_service.mark_overdue_invoices(db_session)

    response = authed_client.get("/api/reports/overdue-invoices")
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    contrato_ids = [f["contrato_id"] for entry in body for f in entry["faturas"]]
    assert contract["id"] in contrato_ids


def test_rental_report_counts_contracts(authed_client):
    _create_and_activate_contract(authed_client, "444.444.444-04", "Cat Relatorio D", dias_passado=10)

    response = authed_client.get("/api/reports/rentals")
    assert response.status_code == 200
    body = response.json()
    assert body["total_contratos"] >= 1


def test_reports_require_authentication(client):
    response = client.get("/api/reports/dashboard")
    assert response.status_code == 401
