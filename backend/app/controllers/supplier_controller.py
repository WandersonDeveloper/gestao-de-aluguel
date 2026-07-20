from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate
from app.services import supplier_service


def create_supplier(db: Session, data: SupplierCreate) -> Supplier:
    return supplier_service.create_supplier(db, data)


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    return supplier_service.get_supplier(db, supplier_id)


def list_suppliers(db: Session, skip: int, limit: int, nome: str | None) -> list[Supplier]:
    return supplier_service.list_suppliers(db, skip=skip, limit=limit, nome=nome)


def update_supplier(db: Session, supplier_id: int, data: SupplierUpdate) -> Supplier:
    return supplier_service.update_supplier(db, supplier_id, data)


def delete_supplier(db: Session, supplier_id: int) -> None:
    supplier_service.delete_supplier(db, supplier_id)
