"""seed dos templates do aditivo

Revision ID: 9a8ff4878c6d
Revises: 5b03cc7e09e9
Create Date: 2026-07-22 16:20:34.914961

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a8ff4878c6d'
down_revision: Union[str, Sequence[str], None] = '5b03cc7e09e9'
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
                "chave": "ADITIVO_CONFIRMACAO",
                "conteudo": (
                    "Olá {cliente_nome}, tudo bem? Vamos adicionar ao seu contrato #{contrato_id}: "
                    "{itens_descricao}, no período de {periodo}.{valor_texto} Precisamos da sua "
                    "confirmação para seguir."
                ),
            },
            {
                "chave": "ADITIVO_ACEITE_CONFIRMADO",
                "conteudo": (
                    "Obrigado, {cliente_nome}! Confirmamos o aceite do item adicional no contrato "
                    "#{contrato_id}. Qualquer dúvida, estamos à disposição!"
                ),
            },
            {
                "chave": "ADITIVO_ACEITE_RECUSADO",
                "conteudo": (
                    "Entendido, {cliente_nome}. Registramos que você não aceitou o item adicional "
                    "no contrato #{contrato_id}. Entre em contato conosco para esclarecer dúvidas "
                    "ou combinar ajustes."
                ),
            },
        ],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DELETE FROM message_templates WHERE chave IN "
        "('ADITIVO_CONFIRMACAO', 'ADITIVO_ACEITE_CONFIRMADO', 'ADITIVO_ACEITE_RECUSADO')"
    )
