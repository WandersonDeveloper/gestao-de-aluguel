from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client


def create(db: Session, data: dict) -> Client:
    client = Client(**data)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


def get(db: Session, client_id: int) -> Client | None:
    return db.get(Client, client_id)


def get_by_documento(db: Session, documento: str) -> Client | None:
    return db.scalar(select(Client).where(Client.documento == documento))


def list_all(db: Session, skip: int = 0, limit: int = 50, nome: str | None = None) -> list[Client]:
    stmt = select(Client)
    if nome:
        stmt = stmt.where(Client.nome.ilike(f"%{nome}%"))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update(db: Session, client: Client, data: dict) -> Client:
    for field, value in data.items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client


def delete(db: Session, client: Client) -> None:
    db.delete(client)
    db.commit()
