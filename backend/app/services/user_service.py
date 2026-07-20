from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError, NotFoundError
from app.models.user import User
from app.repositories import user_repository
from app.schemas.user import UserCreate
from app.utils.security import hash_password


def create_user(db: Session, data: UserCreate) -> User:
    if user_repository.get_by_email(db, data.email):
        raise ConflictError(f"Já existe um usuário com o email {data.email}")
    payload = data.model_dump(exclude={"senha"})
    payload["senha_hash"] = hash_password(data.senha)
    return user_repository.create(db, payload)


def get_user(db: Session, user_id: int) -> User:
    user = user_repository.get(db, user_id)
    if user is None:
        raise NotFoundError(f"Usuário {user_id} não encontrado")
    return user


def list_users(db: Session, skip: int = 0, limit: int = 50) -> list[User]:
    return user_repository.list_all(db, skip=skip, limit=limit)
