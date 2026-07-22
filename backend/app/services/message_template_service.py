from sqlalchemy.orm import Session

from app.domain.exceptions import ConflictError
from app.models.message_template import MessageTemplate, TemplateKey
from app.repositories import message_template_repository

DEFAULT_TEMPLATES: dict[TemplateKey, str] = {
    TemplateKey.COBRANCA_FATURA: (
        "Olá {cliente_nome}, tudo bem? Você tem uma fatura {situacao} no valor de "
        "{valor}, com vencimento em {vencimento}.{multa_texto} Qualquer dúvida, "
        "estamos à disposição!"
    ),
    TemplateKey.CONTRATO_ASSINATURA: (
        "Olá {cliente_nome}, tudo bem? Segue o {tipo_contrato} #{contrato_id} para "
        "sua análise e assinatura. Qualquer dúvida, estamos à disposição!"
    ),
    TemplateKey.ACEITE_CONFIRMADO: (
        "Obrigado, {cliente_nome}! Confirmamos o aceite dos termos do contrato "
        "#{contrato_id}. O prazo de entrega previsto é {prazo_entrega}. Qualquer "
        "dúvida, estamos à disposição!"
    ),
    TemplateKey.ACEITE_RECUSADO: (
        "Entendido, {cliente_nome}. Registramos que você não aceitou os termos do "
        "contrato #{contrato_id}. Entre em contato conosco para esclarecer dúvidas "
        "ou combinar ajustes."
    ),
    TemplateKey.ADITIVO_CONFIRMACAO: (
        "Olá {cliente_nome}, tudo bem? Vamos adicionar ao seu contrato #{contrato_id}: "
        "{itens_descricao}, no período de {periodo}.{valor_texto} Precisamos da sua "
        "confirmação para seguir."
    ),
    TemplateKey.ADITIVO_ACEITE_CONFIRMADO: (
        "Obrigado, {cliente_nome}! Confirmamos o aceite do item adicional no contrato "
        "#{contrato_id}. Qualquer dúvida, estamos à disposição!"
    ),
    TemplateKey.ADITIVO_ACEITE_RECUSADO: (
        "Entendido, {cliente_nome}. Registramos que você não aceitou o item adicional "
        "no contrato #{contrato_id}. Entre em contato conosco para esclarecer dúvidas "
        "ou combinar ajustes."
    ),
}

PLACEHOLDERS: dict[TemplateKey, set[str]] = {
    TemplateKey.COBRANCA_FATURA: {"cliente_nome", "situacao", "valor", "vencimento", "multa_texto"},
    TemplateKey.CONTRATO_ASSINATURA: {"cliente_nome", "tipo_contrato", "contrato_id"},
    TemplateKey.ACEITE_CONFIRMADO: {"cliente_nome", "contrato_id", "prazo_entrega"},
    TemplateKey.ACEITE_RECUSADO: {"cliente_nome", "contrato_id"},
    TemplateKey.ADITIVO_CONFIRMACAO: {"cliente_nome", "contrato_id", "itens_descricao", "periodo", "valor_texto"},
    TemplateKey.ADITIVO_ACEITE_CONFIRMADO: {"cliente_nome", "contrato_id"},
    TemplateKey.ADITIVO_ACEITE_RECUSADO: {"cliente_nome", "contrato_id"},
}


def _validate_conteudo(chave: TemplateKey, conteudo: str) -> None:
    dummy = {nome: "" for nome in PLACEHOLDERS[chave]}
    try:
        conteudo.format(**dummy)
    except KeyError as exc:
        raise ConflictError(f"Variável desconhecida no template: {{{exc.args[0]}}}") from exc
    except (ValueError, IndexError) as exc:
        raise ConflictError(f"Template com formatação inválida: {exc}") from exc


def list_templates(db: Session) -> list[MessageTemplate]:
    return message_template_repository.list_all(db)


def update_template(db: Session, chave: TemplateKey, conteudo: str) -> MessageTemplate:
    _validate_conteudo(chave, conteudo)
    template = message_template_repository.get_by_chave(db, chave)
    if template is None:
        raise ConflictError(f"Template '{chave.value}' não encontrado")
    return message_template_repository.update(db, template, conteudo)


def render(db: Session, chave: TemplateKey, **kwargs: str) -> str:
    template = message_template_repository.get_by_chave(db, chave)
    conteudo = template.conteudo if template is not None else DEFAULT_TEMPLATES[chave]
    return conteudo.format(**kwargs)
