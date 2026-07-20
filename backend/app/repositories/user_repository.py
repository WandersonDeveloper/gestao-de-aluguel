from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def create(db: Session, data: dict) -> User:
    user = User(**data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def list_all(db: Session, skip: int = 0, limit: int = 50) -> list[User]:
    stmt = select(User).offset(skip).limit(limit)
    return list(db.scalars(stmt))
