from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import equipment_category_controller
from app.schemas.equipment_category import (
    EquipmentCategoryCreate,
    EquipmentCategoryRead,
    EquipmentCategoryUpdate,
)
from app.utils.deps import get_current_user

router = APIRouter(
    prefix="/equipment-categories",
    tags=["equipment-categories"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", response_model=EquipmentCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: EquipmentCategoryCreate, db: Session = Depends(get_db)) -> EquipmentCategoryRead:
    return equipment_category_controller.create_category(db, data)


@router.get("", response_model=list[EquipmentCategoryRead])
def list_categories(
    skip: int = 0, limit: int = 50, db: Session = Depends(get_db)
) -> list[EquipmentCategoryRead]:
    return equipment_category_controller.list_categories(db, skip, limit)


@router.get("/{category_id}", response_model=EquipmentCategoryRead)
def get_category(category_id: int, db: Session = Depends(get_db)) -> EquipmentCategoryRead:
    return equipment_category_controller.get_category(db, category_id)


@router.patch("/{category_id}", response_model=EquipmentCategoryRead)
def update_category(
    category_id: int, data: EquipmentCategoryUpdate, db: Session = Depends(get_db)
) -> EquipmentCategoryRead:
    return equipment_category_controller.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: Session = Depends(get_db)) -> None:
    equipment_category_controller.delete_category(db, category_id)
