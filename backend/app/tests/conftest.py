import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from app.config.database import engine, get_db
from app.main import app
from app.models.user import User, UserRole
from app.utils.security import create_access_token, hash_password


@pytest.fixture()
def db_session():
    # Padrão "join a session into an external transaction": os services chamam
    # session.commit()/rollback() normalmente (ex.: contract_service ao tratar
    # IntegrityError de conflito de datas), mas isso só encerra um SAVEPOINT
    # interno — a transação externa do teste é sempre desfeita no final,
    # isolando cada teste sem depender de o código de aplicação nunca commitar.
    connection = engine.connect()
    transaction = connection.begin()
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session: Session = TestSessionLocal()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _create_user(db_session, email: str, papel: UserRole) -> User:
    user = User(
        nome=f"Usuário {papel.value}",
        email=email,
        senha_hash=hash_password("senha123"),
        papel=papel,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_headers(user: User) -> dict:
    token = create_access_token(subject=str(user.id), extra_claims={"papel": user.papel.value})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def admin_user(db_session) -> User:
    return _create_user(db_session, "admin.teste@example.com", UserRole.ADMIN)


@pytest.fixture()
def operador_user(db_session) -> User:
    return _create_user(db_session, "operador.teste@example.com", UserRole.OPERADOR)


@pytest.fixture()
def authed_client(client, admin_user):
    client.headers.update(_auth_headers(admin_user))
    return client


@pytest.fixture()
def operador_client(client, operador_user):
    client.headers.update(_auth_headers(operador_user))
    return client
