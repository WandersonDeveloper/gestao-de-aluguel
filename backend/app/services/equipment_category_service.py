from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError, NotFoundError
from app.models.equipment_category import EquipmentCategory
from app.repositories import equipment_category_repository, equipment_repository
from app.schemas.equipment_category import EquipmentCategoryCreate, EquipmentCategoryUpdate


def create_category(db: Session, data: EquipmentCategoryCreate) -> EquipmentCategory:
    if equipment_category_repository.get_by_nome(db, data.nome):
        raise ConflictError(f"Já existe uma categoria com o nome {data.nome}")
    return equipment_category_repository.create(db, data.model_dump())


def get_category(db: Session, category_id: int) -> EquipmentCategory:
    category = equipment_category_repository.get(db, category_id)
    if category is None:
        raise NotFoundError(f"Categoria {category_id} não encontrada")
    return category


def list_categories(db: Session, skip: int = 0, limit: int = 50) -> list[EquipmentCategory]:
    return equipment_category_repository.list_all(db, skip=skip, limit=limit)


def update_category(db: Session, category_id: int, data: EquipmentCategoryUpdate) -> EquipmentCategory:
    category = get_category(db, category_id)
    updates = data.model_dump(exclude_unset=True)
    if "nome" in updates and updates["nome"] != category.nome:
        existing = equipment_category_repository.get_by_nome(db, updates["nome"])
        if existing is not None:
            raise ConflictError(f"Já existe uma categoria com o nome {updates['nome']}")
    return equipment_category_repository.update(db, category, updates)


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    if equipment_repository.list_all(db, categoria_id=category_id, limit=1):
        raise ConflictError(
            f"Não é possível excluir a categoria {category_id}: existem equipamentos vinculados a ela"
        )
    equipment_category_repository.delete(db, category)
