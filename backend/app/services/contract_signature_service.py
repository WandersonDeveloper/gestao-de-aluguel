import io
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from xhtml2pdf import pisa

from app.config import storage, whatsapp
from app.config.settings import settings
from app.domain.exceptions import NotFoundError
from app.models.contract import OPEN_ENDED_SENTINEL_DATE, Contract, ContractSignatureStatus
from app.models.contract_amendment import ContractAmendment
from app.models.contract_item import ContractItem
from app.models.message_template import TemplateKey
from app.repositories import (
    client_repository,
    contract_amendment_repository,
    contract_item_repository,
    contract_repository,
    equipment_repository,
)
from app.services import message_template_service

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))


def _formatar_datahora(d: datetime) -> str:
    return d.strftime("%d/%m/%Y %H:%M")


def _formatar_data(d) -> str:
    if d is None or d >= OPEN_ENDED_SENTINEL_DATE:
        return "em aberto"
    return d.strftime("%d/%m/%Y")


def _formatar_valor(valor: Decimal) -> str:
    return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def generate_comprovante_pdf(db: Session, contract: Contract) -> bytes:
    cliente = client_repository.get(db, contract.cliente_id)
    template = _env.get_template("comprovante_aceite.html")
    html = template.render(
        gerado_em=_formatar_datahora(datetime.now()),
        empresa={
            "nome": settings.company_name,
            "documento": settings.company_document,
            "endereco": settings.company_address,
        },
        cliente={
            "nome": cliente.nome if cliente else "Cliente não encontrado",
            "documento": cliente.documento if cliente else "—",
            "tipo": cliente.tipo.value if cliente else "PF",
        },
        contrato={"id": contract.id},
        telefone=cliente.telefone if cliente else "—",
        mensagem_enviada=contract.assinatura_mensagem_enviada or "—",
        enviada_em=_formatar_datahora(contract.assinatura_enviada_em) if contract.assinatura_enviada_em else "—",
        resposta_texto=contract.assinatura_resposta_texto or "—",
        confirmada_em=_formatar_datahora(contract.assinatura_confirmada_em)
        if contract.assinatura_confirmada_em
        else "—",
    )

    output = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=output)
    if result.err:
        raise RuntimeError("Falha ao gerar PDF do comprovante de aceite")
    return output.getvalue()


def confirmar(db: Session, contract: Contract, resposta_texto: str, telefone: str) -> Contract:
    contract = contract_repository.update(
        db,
        contract,
        {
            "assinatura_status": ContractSignatureStatus.CONFIRMADO,
            "assinatura_resposta_texto": resposta_texto,
            "assinatura_confirmada_em": datetime.now(),
        },
    )
    pdf_bytes = generate_comprovante_pdf(db, contract)
    key = storage.upload_file(pdf_bytes, f"comprovante_aceite_contrato_{contract.id}.pdf", "application/pdf")
    contract = contract_repository.update(db, contract, {"assinatura_comprovante_key": key})
    db.commit()
    db.refresh(contract)

    cliente = client_repository.get(db, contract.cliente_id)
    if cliente and cliente.telefone:
        mensagem = message_template_service.render(
            db,
            TemplateKey.ACEITE_CONFIRMADO,
            cliente_nome=cliente.nome,
            contrato_id=str(contract.id),
            prazo_entrega=contract.data_inicio.strftime("%d/%m/%Y"),
        )
        whatsapp.send_text(cliente.telefone, mensagem)

    return contract


def recusar(db: Session, contract: Contract, resposta_texto: str, telefone: str) -> Contract:
    contract = contract_repository.update(
        db,
        contract,
        {
            "assinatura_status": ContractSignatureStatus.RECUSADO,
            "assinatura_resposta_texto": resposta_texto,
            "assinatura_confirmada_em": datetime.now(),
        },
    )
    db.commit()
    db.refresh(contract)

    cliente = client_repository.get(db, contract.cliente_id)
    if cliente and cliente.telefone:
        mensagem = message_template_service.render(
            db,
            TemplateKey.ACEITE_RECUSADO,
            cliente_nome=cliente.nome,
            contrato_id=str(contract.id),
        )
        whatsapp.send_text(cliente.telefone, mensagem)

    return contract


def get_comprovante_pdf(db: Session, contract_id: int) -> bytes:
    contract = contract_repository.get(db, contract_id)
    if contract is None:
        raise NotFoundError(f"Contrato {contract_id} não encontrado")
    if not contract.assinatura_comprovante_key:
        raise NotFoundError(f"Contrato {contract_id} ainda não tem assinatura confirmada")
    return storage.download_file(contract.assinatura_comprovante_key)


def _itens_descricao(db: Session, itens: list[ContractItem]) -> str:
    partes = []
    for item in itens:
        equipamento = equipment_repository.get(db, item.equipamento_id)
        nome = equipamento.nome if equipamento else f"Equipamento #{item.equipamento_id}"
        partes.append(f"{nome} x{item.quantidade}")
    return ", ".join(partes)


def enviar_confirmacao_aditivo(
    db: Session,
    amendment: ContractAmendment,
    contract: Contract,
    itens_novos: list[ContractItem],
    valor_aditivo: Decimal | None,
) -> None:
    """Envia ao cliente a confirmação do aditivo (item adicionado a um contrato já
    ativo — ver contract_service.add_items) com as mesmas opções fixas "1"/"2" já
    usadas na assinatura do contrato original. Sem telefone cadastrado, não envia
    nada e o aditivo fica em NAO_ENVIADO (aplicado normalmente, só sem confirmação
    formal registrada)."""
    cliente = client_repository.get(db, contract.cliente_id)
    if cliente is None or not cliente.telefone:
        return

    periodo = f"{_formatar_data(itens_novos[0].data_inicio_item)} até {_formatar_data(itens_novos[0].data_fim_item)}"
    valor_texto = f" O valor adicional será de {_formatar_valor(valor_aditivo)}." if valor_aditivo is not None else ""
    legenda = message_template_service.render(
        db,
        TemplateKey.ADITIVO_CONFIRMACAO,
        cliente_nome=cliente.nome,
        contrato_id=str(contract.id),
        itens_descricao=_itens_descricao(db, itens_novos),
        periodo=periodo,
        valor_texto=valor_texto,
    )
    mensagem_completa = (
        f"{legenda}\n\nPara continuar, responda com o número da opção:\n"
        f"1 - Aceito os termos e condições\n"
        f"2 - Não aceito os termos"
    )
    whatsapp.send_text(cliente.telefone, mensagem_completa)
    contract_amendment_repository.update(
        db,
        amendment,
        {
            "assinatura_status": ContractSignatureStatus.AGUARDANDO_CONFIRMACAO,
            "assinatura_mensagem_enviada": mensagem_completa,
            "assinatura_enviada_em": datetime.now(),
        },
    )


def generate_comprovante_aditivo_pdf(db: Session, amendment: ContractAmendment, contract: Contract) -> bytes:
    cliente = client_repository.get(db, contract.cliente_id)
    itens = [item for item in _itens_amendment(db, amendment)]
    template = _env.get_template("comprovante_aceite_aditivo.html")
    html = template.render(
        gerado_em=_formatar_datahora(datetime.now()),
        empresa={
            "nome": settings.company_name,
            "documento": settings.company_document,
            "endereco": settings.company_address,
        },
        cliente={
            "nome": cliente.nome if cliente else "Cliente não encontrado",
            "documento": cliente.documento if cliente else "—",
            "tipo": cliente.tipo.value if cliente else "PF",
        },
        contrato={"id": contract.id},
        periodo=f"{_formatar_data(amendment.data_anterior)} até {_formatar_data(amendment.data_nova)}",
        itens_descricao=_itens_descricao(db, itens) if itens else "—",
        telefone=cliente.telefone if cliente else "—",
        mensagem_enviada=amendment.assinatura_mensagem_enviada or "—",
        enviada_em=_formatar_datahora(amendment.assinatura_enviada_em) if amendment.assinatura_enviada_em else "—",
        resposta_texto=amendment.assinatura_resposta_texto or "—",
        confirmada_em=_formatar_datahora(amendment.assinatura_confirmada_em)
        if amendment.assinatura_confirmada_em
        else "—",
    )

    output = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=output)
    if result.err:
        raise RuntimeError("Falha ao gerar PDF do comprovante de aceite do aditivo")
    return output.getvalue()


def _itens_amendment(db: Session, amendment: ContractAmendment) -> list[ContractItem]:
    """Itens do contrato que começaram exatamente na data registrada como
    `data_anterior` do aditivo (ver contract_service.add_items, que grava
    data_anterior=hoje/data_nova=data_fim_item ao criar o aditivo) — usado só
    pra montar a descrição no comprovante, não afeta nenhuma regra de negócio."""
    todos = contract_item_repository.list_by_contrato(db, amendment.contrato_id)
    return [item for item in todos if item.data_inicio_item == amendment.data_anterior]


def confirmar_aditivo(db: Session, amendment: ContractAmendment, resposta_texto: str, telefone: str) -> ContractAmendment:
    amendment = contract_amendment_repository.update(
        db,
        amendment,
        {
            "assinatura_status": ContractSignatureStatus.CONFIRMADO,
            "assinatura_resposta_texto": resposta_texto,
            "assinatura_confirmada_em": datetime.now(),
        },
    )
    contract = contract_repository.get(db, amendment.contrato_id)
    pdf_bytes = generate_comprovante_aditivo_pdf(db, amendment, contract)
    key = storage.upload_file(pdf_bytes, f"comprovante_aceite_aditivo_{amendment.id}.pdf", "application/pdf")
    amendment = contract_amendment_repository.update(db, amendment, {"assinatura_comprovante_key": key})
    db.commit()
    db.refresh(amendment)

    cliente = client_repository.get(db, contract.cliente_id)
    if cliente and cliente.telefone:
        mensagem = message_template_service.render(
            db,
            TemplateKey.ADITIVO_ACEITE_CONFIRMADO,
            cliente_nome=cliente.nome,
            contrato_id=str(contract.id),
        )
        whatsapp.send_text(cliente.telefone, mensagem)

    return amendment


def recusar_aditivo(db: Session, amendment: ContractAmendment, resposta_texto: str, telefone: str) -> ContractAmendment:
    """Só registra a recusa — não desfaz item, fatura avulsa ou valor_total
    aplicados em contract_service.add_items (mesmo comportamento já existente
    quando o contrato inteiro é recusado: reverter é uma decisão manual de
    quem administra o contrato, não uma ação automática do sistema)."""
    amendment = contract_amendment_repository.update(
        db,
        amendment,
        {
            "assinatura_status": ContractSignatureStatus.RECUSADO,
            "assinatura_resposta_texto": resposta_texto,
            "assinatura_confirmada_em": datetime.now(),
        },
    )
    db.commit()
    db.refresh(amendment)

    contract = contract_repository.get(db, amendment.contrato_id)
    cliente = client_repository.get(db, contract.cliente_id)
    if cliente and cliente.telefone:
        mensagem = message_template_service.render(
            db,
            TemplateKey.ADITIVO_ACEITE_RECUSADO,
            cliente_nome=cliente.nome,
            contrato_id=str(contract.id),
        )
        whatsapp.send_text(cliente.telefone, mensagem)

    return amendment


def get_comprovante_aditivo_pdf(db: Session, contract_id: int, amendment_id: int) -> bytes:
    amendment = contract_amendment_repository.get(db, amendment_id)
    if amendment is None or amendment.contrato_id != contract_id:
        raise NotFoundError(f"Aditivo {amendment_id} não encontrado no contrato {contract_id}")
    if not amendment.assinatura_comprovante_key:
        raise NotFoundError(f"Aditivo {amendment_id} ainda não tem assinatura confirmada")
    return storage.download_file(amendment.assinatura_comprovante_key)


def _extrair_telefone(data: dict) -> str:
    # O WhatsApp às vezes usa endereçamento "@lid" (linked ID) em
    # `key.remoteJid`, que não é o número de telefone — nesse caso o número
    # de verdade vem em `key.senderPn` (ex.: "556993293771@s.whatsapp.net").
    # Confirmado ao vivo: um remoteJid real chegou como "119005423624412@lid"
    # com `senderPn` dentro de `key` (não em `data` direto, como uma versão
    # anterior deste código assumia por engano — por isso a primeira tentativa
    # de correção não funcionou de verdade, só o teste automatizado, que
    # modelou o payload de teste no lugar errado também).
    key_info = data.get("key") or {}
    sender_pn = key_info.get("senderPn")
    if sender_pn:
        return sender_pn.split("@")[0]
    remote_jid = key_info.get("remoteJid") or ""
    return remote_jid.split("@")[0]


def _extrair_texto_mensagem(data: dict) -> str | None:
    message = data.get("message") or {}
    if "conversation" in message:
        return message["conversation"]
    extended = message.get("extendedTextMessage")
    if extended:
        return extended.get("text")
    return None


def _encontrar_pendente(db: Session, telefone: str) -> tuple[str, Contract | ContractAmendment] | None:
    """Acha o contrato OU aditivo aguardando confirmação cujo cliente tem esse
    telefone — não dá pra saber qual pelo texto da mensagem (só "1"/"2", sem
    número de contrato, pra ficar simples pro cliente), então o telefone é a
    única chave de busca. Se o mesmo telefone tiver mais de uma coisa pendente
    (contrato e aditivo, ou mais de um aditivo — não deveria ser comum), fica
    com a enviada mais recentemente. Retorna ("contrato", Contract) ou
    ("aditivo", ContractAmendment)."""
    candidatos: list[tuple[str, Contract | ContractAmendment, datetime]] = []

    for contract in contract_repository.list_aguardando_confirmacao(db):
        cliente = client_repository.get(db, contract.cliente_id)
        if cliente and cliente.telefone and whatsapp.normalize_phone_br(cliente.telefone) == telefone:
            candidatos.append(("contrato", contract, contract.assinatura_enviada_em or datetime.min))

    for amendment in contract_amendment_repository.list_aguardando_confirmacao(db):
        contract = contract_repository.get(db, amendment.contrato_id)
        cliente = client_repository.get(db, contract.cliente_id) if contract else None
        if cliente and cliente.telefone and whatsapp.normalize_phone_br(cliente.telefone) == telefone:
            candidatos.append(("aditivo", amendment, amendment.assinatura_enviada_em or datetime.min))

    if not candidatos:
        return None
    candidatos.sort(key=lambda c: c[2], reverse=True)
    tipo, alvo, _ = candidatos[0]
    return tipo, alvo


def processar_webhook(db: Session, payload: dict) -> None:
    """Processa um evento recebido da Evolution API. Silencioso em qualquer
    caso que não seja uma opção válida ("1" ou "2") de um cliente com
    contrato/aditivo pendente — o webhook sempre responde 200 pra Evolution
    API, então não há "erro" a reportar pra fora daqui."""
    data = payload.get("data") or {}
    key_info = data.get("key") or {}

    if key_info.get("fromMe"):
        return

    texto = _extrair_texto_mensagem(data)
    if not texto:
        return

    opcao = texto.strip()
    if opcao not in ("1", "2"):
        return

    telefone_respondente = _extrair_telefone(data)
    pendente = _encontrar_pendente(db, telefone_respondente)
    if pendente is None:
        return

    tipo, alvo = pendente
    if tipo == "contrato":
        if opcao == "1":
            confirmar(db, alvo, texto, telefone_respondente)
        else:
            recusar(db, alvo, texto, telefone_respondente)
    else:
        if opcao == "1":
            confirmar_aditivo(db, alvo, texto, telefone_respondente)
        else:
            recusar_aditivo(db, alvo, texto, telefone_respondente)
