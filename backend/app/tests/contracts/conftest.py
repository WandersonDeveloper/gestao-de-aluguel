from datetime import date, timedelta

import pytest


def _create_client(authed_client, documento):
    return authed_client.post(
        "/api/clients",
        json={"nome": "Cliente Contrato", "tipo": "PF", "documento": documento},
    ).json()


def _create_equipment(authed_client, nome_categoria):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    return authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Contrato", "categoria_id": category["id"]}
    ).json()


@pytest.fixture()
def cliente(authed_client):
    return _create_client(authed_client, "555.555.555-55")


@pytest.fixture()
def equipamento(authed_client):
    return _create_equipment(authed_client, "Categoria Contrato")


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
