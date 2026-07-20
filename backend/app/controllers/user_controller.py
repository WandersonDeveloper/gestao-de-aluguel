from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate
from app.services import user_service


def create_user(db: Session, data: UserCreate) -> User:
    return user_service.create_user(db, data)


def get_user(db: Session, user_id: int) -> User:
    return user_service.get_user(db, user_id)


def list_users(db: Session, skip: int, limit: int) -> list[User]:
    return user_service.list_users(db, skip=skip, limit=limit)
