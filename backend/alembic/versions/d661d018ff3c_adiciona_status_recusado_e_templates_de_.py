"""adiciona status recusado e templates de resposta de aceite

Revision ID: d661d018ff3c
Revises: 66da9c7a5e34
Create Date: 2026-07-22 14:56:33.915581

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd661d018ff3c'
down_revision: Union[str, Sequence[str], None] = '66da9c7a5e34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # PostgreSQL exige que um valor novo de ENUM esteja commitado antes de
    # poder ser usado em DML — por isso os ALTER TYPE ficam nesta migration
    # sozinhos, e o INSERT que usa os valores novos fica na migration
    # seguinte (erro visto ao vivo: "unsafe use of new value ... New enum
    # values must be committed before they can be used").
    op.execute("ALTER TYPE contract_signature_status ADD VALUE 'RECUSADO'")
    op.execute("ALTER TYPE template_key ADD VALUE 'ACEITE_CONFIRMADO'")
    op.execute("ALTER TYPE template_key ADD VALUE 'ACEITE_RECUSADO'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL não suporta remover um valor de um tipo ENUM (ALTER TYPE ...
    # DROP VALUE não existe) — reverter exigiria recriar o tipo inteiro e
    # todas as colunas que o usam. Deixado como no-op, mesma limitação
    # assumida em outras migrations aditivas deste projeto.
