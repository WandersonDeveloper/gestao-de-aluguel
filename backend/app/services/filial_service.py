from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError, NotFoundError
from app.models.filial import Filial
from app.repositories import contract_item_repository, equipment_stock_repository, filial_repository
from app.schemas.filial import FilialCreate, FilialUpdate


def create_filial(db: Session, data: FilialCreate) -> Filial:
    if filial_repository.get_by_nome(db, data.nome):
        raise ConflictError(f"Já existe uma filial com o nome {data.nome}")
    return filial_repository.create(db, data.model_dump())


def get_filial(db: Session, filial_id: int) -> Filial:
    filial = filial_repository.get(db, filial_id)
    if filial is None:
        raise NotFoundError(f"Filial {filial_id} não encontrada")
    return filial


def list_filiais(db: Session, skip: int = 0, limit: int = 50) -> list[Filial]:
    return filial_repository.list_all(db, skip=skip, limit=limit)


def update_filial(db: Session, filial_id: int, data: FilialUpdate) -> Filial:
    filial = get_filial(db, filial_id)
    updates = data.model_dump(exclude_unset=True)
    if "nome" in updates and updates["nome"] != filial.nome:
        existing = filial_repository.get_by_nome(db, updates["nome"])
        if existing is not None:
            raise ConflictError(f"Já existe uma filial com o nome {updates['nome']}")
    return filial_repository.update(db, filial, updates)


def delete_filial(db: Session, filial_id: int) -> None:
    filial = get_filial(db, filial_id)
    if equipment_stock_repository.exists_for_filial(db, filial_id):
        raise ConflictError(f"Não é possível excluir a filial {filial_id}: existem equipamentos com estoque vinculado a ela")
    if contract_item_repository.exists_for_filial(db, filial_id):
        raise ConflictError(f"Não é possível excluir a filial {filial_id}: existem itens de contrato vinculados a ela")
    filial_repository.delete(db, filial)
