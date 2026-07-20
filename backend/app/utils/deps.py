from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.domain.exceptions import ForbiddenError, UnauthorizedError
from app.models.user import User, UserRole
from app.repositories import user_repository
from app.utils.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    if token is None:
        raise UnauthorizedError("Não autenticado")
    try:
        payload = decode_access_token(token)
    except JWTError as exc:
        raise UnauthorizedError("Token inválido ou expirado") from exc

    user_id = payload.get("sub")
    user = user_repository.get(db, int(user_id)) if user_id is not None else None
    if user is None or not user.ativo:
        raise UnauthorizedError("Usuário inválido")
    return user


def require_roles(*roles: UserRole):
    def _checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.papel not in roles:
            raise ForbiddenError("Você não tem permissão para executar esta ação")
        return current_user

    return _checker
