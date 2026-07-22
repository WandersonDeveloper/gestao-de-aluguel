"""adiciona tipo (locacao/servico) ao contrato

Revision ID: 0e1bfbe5313d
Revises: 55274102ae44
Create Date: 2026-07-21 04:14:59.347598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0e1bfbe5313d'
down_revision: Union[str, Sequence[str], None] = '55274102ae44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # autogenerate só emite CREATE TYPE quando o enum nasce junto com
    # create_table; como aqui a coluna é adicionada a uma tabela existente,
    # precisa ser manual (mesmo padrão já visto em outras migrations deste projeto).
    op.execute("CREATE TYPE contract_type AS ENUM ('LOCACAO', 'SERVICO')")
    op.add_column('contracts', sa.Column('tipo', sa.Enum('LOCACAO', 'SERVICO', name='contract_type'), server_default='LOCACAO', nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('contracts', 'tipo')
    op.execute("DROP TYPE contract_type")
