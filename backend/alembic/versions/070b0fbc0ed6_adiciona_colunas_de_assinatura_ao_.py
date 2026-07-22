"""adiciona colunas de assinatura ao contract_amendments

Revision ID: 070b0fbc0ed6
Revises: 9a8ff4878c6d
Create Date: 2026-07-22 16:20:35.893950

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '070b0fbc0ed6'
down_revision: Union[str, Sequence[str], None] = '9a8ff4878c6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    contract_signature_status = sa.Enum(
        "NAO_ENVIADO", "AGUARDANDO_CONFIRMACAO", "CONFIRMADO", "RECUSADO",
        name="contract_signature_status", create_type=False,
    )
    op.add_column(
        "contract_amendments",
        sa.Column(
            "assinatura_status", contract_signature_status, server_default="NAO_ENVIADO", nullable=False
        ),
    )
    op.add_column("contract_amendments", sa.Column("assinatura_mensagem_enviada", sa.String(length=2000), nullable=True))
    op.add_column("contract_amendments", sa.Column("assinatura_enviada_em", sa.DateTime(), nullable=True))
    op.add_column("contract_amendments", sa.Column("assinatura_resposta_texto", sa.String(length=500), nullable=True))
    op.add_column("contract_amendments", sa.Column("assinatura_confirmada_em", sa.DateTime(), nullable=True))
    op.add_column("contract_amendments", sa.Column("assinatura_comprovante_key", sa.String(length=255), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contract_amendments", "assinatura_comprovante_key")
    op.drop_column("contract_amendments", "assinatura_confirmada_em")
    op.drop_column("contract_amendments", "assinatura_resposta_texto")
    op.drop_column("contract_amendments", "assinatura_enviada_em")
    op.drop_column("contract_amendments", "assinatura_mensagem_enviada")
    op.drop_column("contract_amendments", "assinatura_status")
