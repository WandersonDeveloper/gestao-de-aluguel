from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError, NotFoundError
from app.models.client import Client
from app.repositories import client_repository
from app.schemas.client import ClientCreate, ClientUpdate


def create_client(db: Session, data: ClientCreate) -> Client:
    if client_repository.get_by_documento(db, data.documento):
        raise ConflictError(f"Já existe um cliente com o documento {data.documento}")
    return client_repository.create(db, data.model_dump())


def get_client(db: Session, client_id: int) -> Client:
    client = client_repository.get(db, client_id)
    if client is None:
        raise NotFoundError(f"Cliente {client_id} não encontrado")
    return client


def list_clients(db: Session, skip: int = 0, limit: int = 50, nome: str | None = None) -> list[Client]:
    return client_repository.list_all(db, skip=skip, limit=limit, nome=nome)


def update_client(db: Session, client_id: int, data: ClientUpdate) -> Client:
    client = get_client(db, client_id)
    updates = data.model_dump(exclude_unset=True)
    if "documento" in updates and updates["documento"] != client.documento:
        existing = client_repository.get_by_documento(db, updates["documento"])
        if existing is not None:
            raise ConflictError(f"Já existe um cliente com o documento {updates['documento']}")
    return client_repository.update(db, client, updates)


def delete_client(db: Session, client_id: int) -> None:
    client = get_client(db, client_id)
    client_repository.delete(db, client)
