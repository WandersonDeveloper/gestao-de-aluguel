from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError, NotFoundError
from app.models.supplier import Supplier
from app.repositories import supplier_repository
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def create_supplier(db: Session, data: SupplierCreate) -> Supplier:
    if data.documento and supplier_repository.get_by_documento(db, data.documento):
        raise ConflictError(f"Já existe um fornecedor com o documento {data.documento}")
    return supplier_repository.create(db, data.model_dump())


def get_supplier(db: Session, supplier_id: int) -> Supplier:
    supplier = supplier_repository.get(db, supplier_id)
    if supplier is None:
        raise NotFoundError(f"Fornecedor {supplier_id} não encontrado")
    return supplier


def list_suppliers(db: Session, skip: int = 0, limit: int = 50, nome: str | None = None) -> list[Supplier]:
    return supplier_repository.list_all(db, skip=skip, limit=limit, nome=nome)


def update_supplier(db: Session, supplier_id: int, data: SupplierUpdate) -> Supplier:
    supplier = get_supplier(db, supplier_id)
    updates = data.model_dump(exclude_unset=True)
    if "documento" in updates and updates["documento"] and updates["documento"] != supplier.documento:
        existing = supplier_repository.get_by_documento(db, updates["documento"])
        if existing is not None:
            raise ConflictError(f"Já existe um fornecedor com o documento {updates['documento']}")
    return supplier_repository.update(db, supplier, updates)


def delete_supplier(db: Session, supplier_id: int) -> None:
    supplier = get_supplier(db, supplier_id)
    supplier_repository.delete(db, supplier)
