from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier


def create(db: Session, data: dict) -> Supplier:
    supplier = Supplier(**data)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def get(db: Session, supplier_id: int) -> Supplier | None:
    return db.get(Supplier, supplier_id)


def get_by_documento(db: Session, documento: str) -> Supplier | None:
    return db.scalar(select(Supplier).where(Supplier.documento == documento))


def list_all(db: Session, skip: int = 0, limit: int = 50, nome: str | None = None) -> list[Supplier]:
    stmt = select(Supplier)
    if nome:
        stmt = stmt.where(Supplier.nome.ilike(f"%{nome}%"))
    stmt = stmt.offset(skip).limit(limit)
    return list(db.scalars(stmt))


def update(db: Session, supplier: Supplier, data: dict) -> Supplier:
    for field, value in data.items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


def delete(db: Session, supplier: Supplier) -> None:
    db.delete(supplier)
    db.commit()
