from sqlalchemy.orm import Session

from app.models.client import Client
from app.schemas.client import ClientCreate, ClientUpdate
from app.services import client_service


def create_client(db: Session, data: ClientCreate) -> Client:
    return client_service.create_client(db, data)


def get_client(db: Session, client_id: int) -> Client:
    return client_service.get_client(db, client_id)


def list_clients(db: Session, skip: int, limit: int, nome: str | None) -> list[Client]:
    return client_service.list_clients(db, skip=skip, limit=limit, nome=nome)


def update_client(db: Session, client_id: int, data: ClientUpdate) -> Client:
    return client_service.update_client(db, client_id, data)


def delete_client(db: Session, client_id: int) -> None:
    client_service.delete_client(db, client_id)
