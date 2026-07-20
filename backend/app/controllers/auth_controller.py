from sqlalchemy.orm import Session

from app.schemas.auth import Token
from app.services import auth_service


def login(db: Session, email: str, senha: str) -> Token:
    user = auth_service.authenticate(db, email, senha)
    token = auth_service.issue_token(user)
    return Token(access_token=token)
