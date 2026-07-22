"""seed dos templates de resposta de aceite

Revision ID: 64df57365aca
Revises: d661d018ff3c
Create Date: 2026-07-22 14:57:51.891960

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64df57365aca'
down_revision: Union[str, Sequence[str], None] = 'd661d018ff3c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    message_templates = sa.table(
        "message_templates",
        sa.column("chave", sa.String),
        sa.column("conteudo", sa.String),
    )
    op.bulk_insert(
        message_templates,
        [
            {
                "chave": "ACEITE_CONFIRMADO",
                "conteudo": (
                    "Obrigado, {cliente_nome}! Confirmamos o aceite dos termos do contrato "
                    "#{contrato_id}. O prazo de entrega previsto é {prazo_entrega}. Qualquer "
                    "dúvida, estamos à disposição!"
                ),
            },
            {
                "chave": "ACEITE_RECUSADO",
                "conteudo": (
                    "Entendido, {cliente_nome}. Registramos que você não aceitou os termos do "
                    "contrato #{contrato_id}. Entre em contato conosco para esclarecer dúvidas "
                    "ou combinar ajustes."
                ),
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM message_templates WHERE chave IN ('ACEITE_CONFIRMADO', 'ACEITE_RECUSADO')")
