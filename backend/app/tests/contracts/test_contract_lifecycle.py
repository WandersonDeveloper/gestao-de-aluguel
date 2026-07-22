from datetime import timedelta


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


def test_activate_contract_with_start_today_rents_equipment_immediately(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.post(f"/api/contracts/{contract['id']}/activate")
    assert response.status_code == 200
    assert response.json()["status"] == "ativo"

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "alugado"


def test_activate_contract_with_future_start_only_reserves_equipment(
    authed_client, cliente, equipamento, filial, periodo_futuro
):
    inicio, fim = periodo_futuro
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.post(f"/api/contracts/{contract['id']}/activate")
    assert response.status_code == 200

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "reservado"


def test_cannot_activate_already_active_contract(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.post(f"/api/contracts/{contract['id']}/activate")
    assert response.status_code == 409


def test_baixa_total_frees_equipment_and_closes_contract(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={"motivo": "Fim do aluguel"})
    assert response.status_code == 200
    assert response.json()["status"] == "encerrado"

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_baixa_total_blocked_when_invoice_pending(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "500.00",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    faturas = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert any(f["status"] == "pendente" for f in faturas)

    response = authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={"motivo": "Fim do aluguel"})
    assert response.status_code == 409

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] != "disponivel"


def test_baixa_total_allowed_after_invoices_settled(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": "500.00",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    faturas = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    for fatura in faturas:
        authed_client.post(f"/api/invoices/{fatura['id']}/cancel")

    response = authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={"motivo": "Fim do aluguel"})
    assert response.status_code == 200
    assert response.json()["status"] == "encerrado"


def test_baixa_parcial_allowed_even_with_invoice_pending(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equip_a = authed_client.post("/api/equipment-categories", json={"nome": "Cat Parcial Pendente"}).json()
    equipamento_a = authed_client.post(
        "/api/equipment", json={"nome": "Equip Parcial Pendente A", "categoria_id": equip_a["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento_a['id']}/estoque/{filial['id']}", json={"quantidade": 1})
    equipamento_b = authed_client.post(
        "/api/equipment", json={"nome": "Equip Parcial Pendente B", "categoria_id": equip_a["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipamento_b['id']}/estoque/{filial['id']}", json={"quantidade": 1})

    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [
                {"equipamento_id": equipamento_a["id"], "filial_id": filial["id"], "quantidade": 1},
                {"equipamento_id": equipamento_b["id"], "filial_id": filial["id"], "quantidade": 1},
            ],
            "valor_total": "500.00",
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    itens = authed_client.get(f"/api/contracts/{contract['id']}").json()["itens"]

    response = authed_client.post(
        f"/api/contracts/{contract['id']}/baixa", json={"item_ids": [itens[0]["id"]], "motivo": "Devolução parcial"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ativo"


def test_baixa_parcial_keeps_contract_active_until_all_items_returned(authed_client, cliente, filial, periodo_atual):
    inicio, fim = periodo_atual
    equip_a = authed_client.post(
        "/api/equipment-categories", json={"nome": "Cat Parcial"}
    ).json()
    eq1 = authed_client.post(
        "/api/equipment", json={"nome": "Equip 1", "categoria_id": equip_a["id"]}
    ).json()
    eq2 = authed_client.post(
        "/api/equipment", json={"nome": "Equip 2", "categoria_id": equip_a["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{eq1['id']}/estoque/{filial['id']}", json={"quantidade": 1})
    authed_client.put(f"/api/equipment/{eq2['id']}/estoque/{filial['id']}", json={"quantidade": 1})

    contract = authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [
                {"equipamento_id": eq1["id"], "filial_id": filial["id"], "quantidade": 1},
                {"equipamento_id": eq2["id"], "filial_id": filial["id"], "quantidade": 1},
            ],
        },
    ).json()
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    itens = authed_client.get(f"/api/contracts/{contract['id']}").json()["itens"]
    item_eq1 = next(i for i in itens if i["equipamento_id"] == eq1["id"])

    # Baixa parcial: devolve só o item do eq1.
    partial = authed_client.post(
        f"/api/contracts/{contract['id']}/baixa", json={"item_ids": [item_eq1["id"]]}
    )
    assert partial.status_code == 200
    assert partial.json()["status"] == "ativo"
    assert authed_client.get(f"/api/equipment/{eq1['id']}").json()["status"] == "disponivel"
    assert authed_client.get(f"/api/equipment/{eq2['id']}").json()["status"] == "alugado"

    # Baixa total dos itens restantes: agora sim o contrato encerra.
    final = authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={})
    assert final.status_code == 200
    assert final.json()["status"] == "encerrado"


def test_extend_contract_creates_amendment_and_updates_data_fim(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    nova_data_fim = fim + timedelta(days=10)
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/extend",
        json={"nova_data_fim": nova_data_fim.isoformat(), "motivo": "Cliente pediu mais tempo"},
    )
    assert response.status_code == 200
    assert response.json()["data_fim"] == nova_data_fim.isoformat()

    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    assert len(amendments) == 1
    assert amendments[0]["tipo"] == "extensao"
    assert amendments[0]["data_nova"] == nova_data_fim.isoformat()


def test_extend_contract_with_earlier_date_is_rejected(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.post(
        f"/api/contracts/{contract['id']}/extend",
        json={"nova_data_fim": (fim - timedelta(days=1)).isoformat()},
    )
    assert response.status_code == 409


def test_cancel_contract_frees_equipment(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    response = authed_client.post(f"/api/contracts/{contract['id']}/cancel", json={"motivo": "Desistência"})
    assert response.status_code == 200
    assert response.json()["status"] == "cancelado"

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_cancel_draft_contract_does_not_touch_equipment(
    authed_client, cliente, equipamento, filial, periodo_futuro
):
    inicio, fim = periodo_futuro
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.post(f"/api/contracts/{contract['id']}/cancel", json={})
    assert response.status_code == 200

    equipamento_atualizado = authed_client.get(f"/api/equipment/{equipamento['id']}").json()
    assert equipamento_atualizado["status"] == "disponivel"


def test_cannot_dar_baixa_on_draft_contract(authed_client, cliente, equipamento, filial, periodo_futuro):
    inicio, fim = periodo_futuro
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.post(f"/api/contracts/{contract['id']}/baixa", json={})
    assert response.status_code == 409


def test_delete_equipment_linked_to_contract_conflicts(
    authed_client, cliente, equipamento, filial, periodo_futuro
):
    inicio, fim = periodo_futuro
    # Basta o equipamento ter um item de contrato (mesmo em rascunho) para bloquear a exclusão.
    _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    response = authed_client.delete(f"/api/equipment/{equipamento['id']}")
    assert response.status_code == 409
