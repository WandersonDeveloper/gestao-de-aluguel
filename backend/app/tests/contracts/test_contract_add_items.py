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


def _create_contract_with_valor_total(authed_client, cliente, equipamento, filial, inicio, fim, valor_total):
    return authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "valor_total": valor_total,
        },
    ).json()


def _create_contract_with_periodicidade(authed_client, cliente, equipamento, filial, inicio, fim, periodicidade):
    return authed_client.post(
        "/api/contracts",
        json={
            "cliente_id": cliente["id"],
            "data_inicio": inicio.isoformat(),
            "data_fim": fim.isoformat(),
            "itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "periodicidade_cobranca": periodicidade,
        },
    ).json()


def _create_second_equipment(authed_client, filial, quantidade=1, valor_diario=None, valor_mensal=None):
    category = authed_client.post("/api/equipment-categories", json={"nome": "Cat Aditivo"}).json()
    equipment = authed_client.post(
        "/api/equipment", json={"nome": "Andaime Extra", "categoria_id": category["id"]}
    ).json()
    estoque_payload = {"quantidade": quantidade}
    if valor_diario is not None:
        estoque_payload["valor_diario"] = valor_diario
    if valor_mensal is not None:
        estoque_payload["valor_mensal"] = valor_mensal
    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial['id']}", json=estoque_payload)
    return equipment


def test_add_items_to_active_contract_generates_addendum_invoice(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual  # 6 dias corridos (hoje até hoje+5, inclusive)
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    novo_equipamento = _create_second_equipment(authed_client, filial, valor_diario="25.00")
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={
            "itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "condicao_cobranca_item": "diaria",
            "motivo": "Cliente pediu mais andaimes",
        },
    )
    assert response.status_code == 200

    itens = authed_client.get(f"/api/contracts/{contract['id']}").json()["itens"]
    assert any(item["equipamento_id"] == novo_equipamento["id"] for item in itens)

    faturas = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    # 25.00 * 1 unidade * 6 dias = 150.00 — calculado automaticamente pelo
    # backend a partir do valor_diario escolhido como condição de cobrança.
    fatura_aditivo = next(f for f in faturas if f["valor"] == "150.00")
    assert fatura_aditivo is not None

    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    aditivo = next(a for a in amendments if a["tipo"] == "adicao_item")
    assert any(item["equipamento_id"] == novo_equipamento["id"] for item in aditivo["itens"])


def test_add_items_without_valor_aditivo_does_not_generate_invoice(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    faturas_antes = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()

    novo_equipamento = _create_second_equipment(authed_client, filial)
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 200

    faturas_depois = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(faturas_depois) == len(faturas_antes)


def test_add_items_fails_when_stock_insufficient(authed_client, cliente, equipamento, filial, periodo_atual):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    # `equipamento` só tem quantidade 1 na filial, e já está todo reservado pelo próprio contrato.
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 409


def test_add_items_requires_active_contract(authed_client, cliente, equipamento, filial, periodo_futuro):
    inicio, fim = periodo_futuro
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)

    novo_equipamento = _create_second_equipment(authed_client, filial)
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 409


def test_add_items_accumulates_valor_total_when_contract_has_fixed_total(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual  # 6 dias corridos (hoje até hoje+5, inclusive)
    contract = _create_contract_with_valor_total(
        authed_client, cliente, equipamento, filial, inicio, fim, "1000.00"
    )
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    novo_equipamento = _create_second_equipment(authed_client, filial, valor_diario="25.00")
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={
            "itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "condicao_cobranca_item": "diaria",
        },
    )
    assert response.status_code == 200
    assert response.json()["valor_total"] == "1150.00"

    contrato_atualizado = authed_client.get(f"/api/contracts/{contract['id']}").json()
    assert contrato_atualizado["valor_total"] == "1150.00"


def test_add_items_calculates_valor_aditivo_automatically_for_diaria_contract(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual  # 6 dias corridos (hoje até hoje+5, inclusive)
    contract = _create_contract_with_periodicidade(
        authed_client, cliente, equipamento, filial, inicio, fim, "diaria"
    )
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    novo_equipamento = _create_second_equipment(authed_client, filial, quantidade=2, valor_diario="10.00")
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 2}]},
    )
    assert response.status_code == 200

    faturas = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    # 10.00 * 2 unidades * 6 dias = 120.00 — não foi informado manualmente, o
    # backend calculou a partir do valor_diario cadastrado no estoque.
    fatura_aditivo = next(f for f in faturas if f["valor"] == "120.00")
    assert fatura_aditivo is not None


def test_add_items_calculates_valor_aditivo_automatically_for_mensal_contract(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract_with_periodicidade(
        authed_client, cliente, equipamento, filial, inicio, fim, "mensal"
    )
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    novo_equipamento = _create_second_equipment(authed_client, filial, valor_mensal="300.00")
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 200

    faturas = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    # Período curto (5 dias) cabe em 1 mensalidade — 300.00 * 1 unidade * 1 mês.
    fatura_aditivo = next(f for f in faturas if f["valor"] == "300.00")
    assert fatura_aditivo is not None


def test_add_items_fails_when_diaria_equipment_missing_valor_diario(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract_with_periodicidade(
        authed_client, cliente, equipamento, filial, inicio, fim, "diaria"
    )
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    # Sem valor_diario cadastrado no estoque — não dá pra calcular o aditivo.
    novo_equipamento = _create_second_equipment(authed_client, filial)
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 409


def test_add_items_hourly_does_not_generate_addendum_invoice(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract_with_periodicidade(
        authed_client, cliente, equipamento, filial, inicio, fim, "hora"
    )
    authed_client.post(f"/api/contracts/{contract['id']}/activate")
    faturas_antes = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()

    # Mesmo com valor_hora cadastrado, cobrança por hora não gera fatura na
    # adição — é cobrada na baixa, junto com o resto do contrato.
    novo_equipamento = _create_second_equipment(authed_client, filial)
    authed_client.put(
        f"/api/equipment/{novo_equipamento['id']}/estoque/{filial['id']}",
        json={"quantidade": 1, "valor_hora": "50.00"},
    )
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 200

    faturas_depois = authed_client.get("/api/invoices", params={"contrato_id": contract["id"]}).json()
    assert len(faturas_depois) == len(faturas_antes)


def test_add_items_records_period_in_amendment_history(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    novo_equipamento = _create_second_equipment(authed_client, filial)
    authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={"itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}]},
    )

    amendments = authed_client.get(f"/api/contracts/{contract['id']}/amendments").json()
    aditivo = next(a for a in amendments if a["tipo"] == "adicao_item")
    assert aditivo["data_anterior"] == inicio.isoformat()
    assert aditivo["data_nova"] == fim.isoformat()


def test_add_items_rejects_hora_as_condicao_cobranca_item_for_unica_contract(
    authed_client, cliente, equipamento, filial, periodo_atual
):
    inicio, fim = periodo_atual
    contract = _create_contract(authed_client, cliente, equipamento, filial, inicio, fim)
    authed_client.post(f"/api/contracts/{contract['id']}/activate")

    novo_equipamento = _create_second_equipment(authed_client, filial)
    authed_client.put(
        f"/api/equipment/{novo_equipamento['id']}/estoque/{filial['id']}",
        json={"quantidade": 1, "valor_hora": "50.00"},
    )
    response = authed_client.post(
        f"/api/contracts/{contract['id']}/add-items",
        json={
            "itens": [{"equipamento_id": novo_equipamento["id"], "filial_id": filial["id"], "quantidade": 1}],
            "condicao_cobranca_item": "hora",
        },
    )
    assert response.status_code == 409


def test_add_items_requires_existing_contract(authed_client, filial):
    response = authed_client.post(
        "/api/contracts/999999/add-items",
        json={"itens": [{"equipamento_id": 1, "filial_id": filial["id"], "quantidade": 1}]},
    )
    assert response.status_code == 404
