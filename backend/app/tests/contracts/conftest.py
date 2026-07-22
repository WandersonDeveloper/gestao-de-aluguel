from datetime import date, timedelta

import pytest


def _create_client(authed_client, documento):
    return authed_client.post(
        "/api/clients",
        json={"nome": "Cliente Contrato", "tipo": "PF", "documento": documento},
    ).json()


def _create_filial(authed_client, nome):
    return authed_client.post("/api/filiais", json={"nome": nome}).json()


def _create_equipment_with_stock(authed_client, nome_categoria, filial_id, quantidade=1):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    equipment = authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Contrato", "categoria_id": category["id"]}
    ).json()
    authed_client.put(f"/api/equipment/{equipment['id']}/estoque/{filial_id}", json={"quantidade": quantidade})
    return equipment


@pytest.fixture()
def cliente(authed_client):
    return _create_client(authed_client, "555.555.555-55")


@pytest.fixture()
def filial(authed_client):
    return _create_filial(authed_client, "Filial Contrato")


@pytest.fixture()
def equipamento(authed_client, filial):
    return _create_equipment_with_stock(authed_client, "Categoria Contrato", filial["id"])


@pytest.fixture()
def periodo_futuro():
    inicio = date.today() + timedelta(days=10)
    fim = inicio + timedelta(days=5)
    return inicio, fim


@pytest.fixture()
def periodo_atual():
    inicio = date.today()
    fim = inicio + timedelta(days=5)
    return inicio, fim
