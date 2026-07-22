"""adiciona tipo adicao_item ao contract_amendment_type

Revision ID: 2711ff0b44fb
Revises: 64df57365aca
Create Date: 2026-07-22 15:37:13.058403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2711ff0b44fb'
down_revision: Union[str, Sequence[str], None] = '64df57365aca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE contract_amendment_type ADD VALUE 'ADICAO_ITEM'")


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL não suporta remover um valor de ENUM (ver migration
    # d661d018ff3c para a mesma limitação já documentada) — no-op.
