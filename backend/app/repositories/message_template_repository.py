from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.message_template import MessageTemplate, TemplateKey


def get_by_chave(db: Session, chave: TemplateKey) -> MessageTemplate | None:
    return db.scalar(select(MessageTemplate).where(MessageTemplate.chave == chave))


def list_all(db: Session) -> list[MessageTemplate]:
    return list(db.scalars(select(MessageTemplate)))


def update(db: Session, template: MessageTemplate, conteudo: str) -> MessageTemplate:
    template.conteudo = conteudo
    db.commit()
    db.refresh(template)
    return template
