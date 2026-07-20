from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import supplier_controller
from app.schemas.supplier import SupplierCreate, SupplierRead, SupplierUpdate
from app.utils.deps import get_current_user

router = APIRouter(prefix="/suppliers", tags=["suppliers"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(data: SupplierCreate, db: Session = Depends(get_db)) -> SupplierRead:
    return supplier_controller.create_supplier(db, data)


@router.get("", response_model=list[SupplierRead])
def list_suppliers(
    skip: int = 0, limit: int = 50, nome: str | None = None, db: Session = Depends(get_db)
) -> list[SupplierRead]:
    return supplier_controller.list_suppliers(db, skip, limit, nome)


@router.get("/{supplier_id}", response_model=SupplierRead)
def get_supplier(supplier_id: int, db: Session = Depends(get_db)) -> SupplierRead:
    return supplier_controller.get_supplier(db, supplier_id)


@router.patch("/{supplier_id}", response_model=SupplierRead)
def update_supplier(supplier_id: int, data: SupplierUpdate, db: Session = Depends(get_db)) -> SupplierRead:
    return supplier_controller.update_supplier(db, supplier_id, data)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)) -> None:
    supplier_controller.delete_supplier(db, supplier_id)
