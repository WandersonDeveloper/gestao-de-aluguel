from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.controllers import client_controller
from app.schemas.client import ClientCreate, ClientRead, ClientUpdate
from app.utils.deps import get_current_user

router = APIRouter(prefix="/clients", tags=["clients"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
def create_client(data: ClientCreate, db: Session = Depends(get_db)) -> ClientRead:
    return client_controller.create_client(db, data)


@router.get("", response_model=list[ClientRead])
def list_clients(
    skip: int = 0,
    limit: int = 50,
    nome: str | None = None,
    db: Session = Depends(get_db),
) -> list[ClientRead]:
    return client_controller.list_clients(db, skip, limit, nome)


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: Session = Depends(get_db)) -> ClientRead:
    return client_controller.get_client(db, client_id)


@router.patch("/{client_id}", response_model=ClientRead)
def update_client(client_id: int, data: ClientUpdate, db: Session = Depends(get_db)) -> ClientRead:
    return client_controller.update_client(db, client_id, data)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, db: Session = Depends(get_db)) -> None:
    client_controller.delete_client(db, client_id)
