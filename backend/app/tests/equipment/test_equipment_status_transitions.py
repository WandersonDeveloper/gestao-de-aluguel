def _create_equipment(authed_client, nome_categoria="Categoria Transição"):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    return authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Transição", "categoria_id": category["id"]}
    ).json()


def test_valid_transition_disponivel_to_reservado(authed_client):
    equipment = _create_equipment(authed_client, "Cat A")
    response = authed_client.post(
        f"/api/equipment/{equipment['id']}/status", json={"status": "reservado", "motivo": "Reserva para contrato X"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "reservado"


def test_full_cycle_disponivel_reservado_alugado_disponivel(authed_client):
    equipment = _create_equipment(authed_client, "Cat B")
    eq_id = equipment["id"]

    r1 = authed_client.post(f"/api/equipment/{eq_id}/status", json={"status": "reservado"})
    assert r1.status_code == 200

    r2 = authed_client.post(f"/api/equipment/{eq_id}/status", json={"status": "alugado"})
    assert r2.status_code == 200

    r3 = authed_client.post(f"/api/equipment/{eq_id}/status", json={"status": "disponivel"})
    assert r3.status_code == 200
    assert r3.json()["status"] == "disponivel"


def test_invalid_transition_disponivel_to_alugado_is_rejected(authed_client):
    equipment = _create_equipment(authed_client, "Cat C")
    response = authed_client.post(
        f"/api/equipment/{equipment['id']}/status", json={"status": "alugado"}
    )
    assert response.status_code == 409


def test_invalid_transition_manutencao_to_alugado_is_rejected(authed_client):
    equipment = _create_equipment(authed_client, "Cat D")
    eq_id = equipment["id"]
    authed_client.post(f"/api/equipment/{eq_id}/status", json={"status": "manutencao"})

    response = authed_client.post(f"/api/equipment/{eq_id}/status", json={"status": "alugado"})
    assert response.status_code == 409


def test_transition_records_movement_history(authed_client):
    equipment = _create_equipment(authed_client, "Cat E")
    eq_id = equipment["id"]
    authed_client.post(
        f"/api/equipment/{eq_id}/status", json={"status": "manutencao", "motivo": "Revisão preventiva"}
    )

    response = authed_client.get(f"/api/equipment/{eq_id}/movements")
    assert response.status_code == 200
    movements = response.json()
    assert len(movements) == 1
    assert movements[0]["status_anterior"] == "disponivel"
    assert movements[0]["status_novo"] == "manutencao"
    assert movements[0]["motivo"] == "Revisão preventiva"
    assert movements[0]["usuario_id"] is not None


def test_status_transition_requires_authentication(client, admin_user):
    from app.utils.security import create_access_token

    headers = {"Authorization": f"Bearer {create_access_token(subject=str(admin_user.id))}"}
    category = client.post(
        "/api/equipment-categories", json={"nome": "Cat F"}, headers=headers
    ).json()
    equipment = client.post(
        "/api/equipment",
        json={"nome": "Equip F", "categoria_id": category["id"]},
        headers=headers,
    ).json()

    # Sem header de autorização nesta chamada: deve ser rejeitado.
    response = client.post(f"/api/equipment/{equipment['id']}/status", json={"status": "reservado"})
    assert response.status_code == 401
