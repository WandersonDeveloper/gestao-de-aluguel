from sqlalchemy.orm import Session

from app.domain.exceptions import UnauthorizedError
from app.models.user import User
from app.repositories import user_repository
from app.utils.security import create_access_token, verify_password


def authenticate(db: Session, email: str, senha: str) -> User:
    user = user_repository.get_by_email(db, email)
    if user is None or not user.ativo or not verify_password(senha, user.senha_hash):
        raise UnauthorizedError("Email ou senha inválidos")
    return user


def issue_token(user: User) -> str:
    return create_access_token(subject=str(user.id), extra_claims={"papel": user.papel.value})
