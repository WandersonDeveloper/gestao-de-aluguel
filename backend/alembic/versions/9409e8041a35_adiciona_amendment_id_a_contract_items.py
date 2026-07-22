"""adiciona amendment_id a contract_items

Revision ID: 9409e8041a35
Revises: 070b0fbc0ed6
Create Date: 2026-07-22 16:44:58.643543

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9409e8041a35'
down_revision: Union[str, Sequence[str], None] = '070b0fbc0ed6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("contract_items", sa.Column("amendment_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_contract_items_amendment_id", "contract_items", "contract_amendments", ["amendment_id"], ["id"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_contract_items_amendment_id", "contract_items", type_="foreignkey")
    op.drop_column("contract_items", "amendment_id")
