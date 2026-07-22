"""adiciona chaves de template do aditivo

Revision ID: 5b03cc7e09e9
Revises: 2711ff0b44fb
Create Date: 2026-07-22 16:20:34.087590

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5b03cc7e09e9'
down_revision: Union[str, Sequence[str], None] = '2711ff0b44fb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE template_key ADD VALUE 'ADITIVO_CONFIRMACAO'")
    op.execute("ALTER TYPE template_key ADD VALUE 'ADITIVO_ACEITE_CONFIRMADO'")
    op.execute("ALTER TYPE template_key ADD VALUE 'ADITIVO_ACEITE_RECUSADO'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL não suporta remover valor de enum diretamente — sem downgrade real aqui,
    # mesma limitação já aceita nas migrations anteriores que adicionam valor de enum.
    pass
