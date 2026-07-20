import os

from app.config.database import SessionLocal
from app.models.user import UserRole
from app.repositories import user_repository
from app.utils.security import hash_password


def run() -> None:
    email = os.environ.get("ADMIN_EMAIL", "admin@example.com")
    senha = os.environ.get("ADMIN_PASSWORD", "admin123")

    db = SessionLocal()
    try:
        if user_repository.get_by_email(db, email):
            print(f"Usuário admin '{email}' já existe.")
            return
        user_repository.create(
            db,
            {
                "nome": "Administrador",
                "email": email,
                "senha_hash": hash_password(senha),
                "papel": UserRole.ADMIN,
            },
        )
        print(f"Usuário admin '{email}' criado com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
