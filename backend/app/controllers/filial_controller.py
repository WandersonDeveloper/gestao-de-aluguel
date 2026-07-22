from sqlalchemy.orm import Session

from app.models.filial import Filial
from app.schemas.filial import FilialCreate, FilialUpdate
from app.services import filial_service


def create_filial(db: Session, data: FilialCreate) -> Filial:
    return filial_service.create_filial(db, data)


def get_filial(db: Session, filial_id: int) -> Filial:
    return filial_service.get_filial(db, filial_id)


def list_filiais(db: Session, skip: int, limit: int) -> list[Filial]:
    return filial_service.list_filiais(db, skip=skip, limit=limit)


def update_filial(db: Session, filial_id: int, data: FilialUpdate) -> Filial:
    return filial_service.update_filial(db, filial_id, data)


def delete_filial(db: Session, filial_id: int) -> None:
    filial_service.delete_filial(db, filial_id)
