from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import filial_controller
from app.models.user import User, UserRole
from app.schemas.filial import FilialCreate, FilialRead, FilialUpdate
from app.utils.deps import get_current_user, require_roles

router = APIRouter(prefix="/filiais", tags=["filiais"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=FilialRead, status_code=status.HTTP_201_CREATED)
def create_filial(
    data: FilialCreate, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))
) -> FilialRead:
    return filial_controller.create_filial(db, data)


@router.get("", response_model=list[FilialRead])
def list_filiais(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)) -> list[FilialRead]:
    return filial_controller.list_filiais(db, skip, limit)


@router.get("/{filial_id}", response_model=FilialRead)
def get_filial(filial_id: int, db: Session = Depends(get_db)) -> FilialRead:
    return filial_controller.get_filial(db, filial_id)


@router.patch("/{filial_id}", response_model=FilialRead)
def update_filial(
    filial_id: int,
    data: FilialUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> FilialRead:
    return filial_controller.update_filial(db, filial_id, data)


@router.delete("/{filial_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_filial(
    filial_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles(UserRole.ADMIN))
) -> None:
    filial_controller.delete_filial(db, filial_id)
