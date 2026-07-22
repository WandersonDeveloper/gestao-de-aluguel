from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.filial import Filial


def create(db: Session, data: dict) -> Filial:
    filial = Filial(**data)
    db.add(filial)
    db.commit()
    db.refresh(filial)
    return filial


def get(db: Session, filial_id: int) -> Filial | None:
    return db.get(Filial, filial_id)


def get_by_nome(db: Session, nome: str) -> Filial | None:
    return db.scalar(select(Filial).where(Filial.nome == nome))


def list_all(db: Session, skip: int = 0, limit: int = 50) -> list[Filial]:
    stmt = select(Filial).offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update(db: Session, filial: Filial, data: dict) -> Filial:
    for field, value in data.items():
        setattr(filial, field, value)
    db.commit()
    db.refresh(filial)
    return filial


def delete(db: Session, filial: Filial) -> None:
    db.delete(filial)
    db.commit()
