def _create_equipment(authed_client, nome_categoria="Categoria Fotos"):
    category = authed_client.post("/api/equipment-categories", json={"nome": nome_categoria}).json()
    return authed_client.post(
        "/api/equipment", json={"nome": "Equipamento Fotos", "categoria_id": category["id"]}
    ).json()


def test_upload_and_list_photo(authed_client):
    equipamento = _create_equipment(authed_client, "Cat Foto A")
    files = {"file": ("foto.jpg", b"fake-image-bytes", "image/jpeg")}

    response = authed_client.post(f"/api/equipment/{equipamento['id']}/photos", files=files)
    assert response.status_code == 201
    body = response.json()
    assert body["key"].endswith(".jpg")
    assert body["url"].startswith("http")

    list_response = authed_client.get(f"/api/equipment/{equipamento['id']}/photos")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["key"] == body["key"]


def test_delete_photo(authed_client):
    equipamento = _create_equipment(authed_client, "Cat Foto B")
    files = {"file": ("foto.png", b"fake-image-bytes", "image/png")}
    uploaded = authed_client.post(f"/api/equipment/{equipamento['id']}/photos", files=files).json()

    response = authed_client.delete(f"/api/equipment/{equipamento['id']}/photos/{uploaded['key']}")
    assert response.status_code == 204

    list_response = authed_client.get(f"/api/equipment/{equipamento['id']}/photos")
    assert list_response.json() == []


def test_delete_missing_photo_returns_404(authed_client):
    equipamento = _create_equipment(authed_client, "Cat Foto C")
    response = authed_client.delete(f"/api/equipment/{equipamento['id']}/photos/chave-inexistente.jpg")
    assert response.status_code == 404


def test_photo_endpoints_require_authentication(client):
    response = client.get("/api/equipment/1/photos")
    assert response.status_code == 401
