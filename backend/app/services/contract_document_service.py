import base64
import io
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session
from xhtml2pdf import pisa

from app.config import whatsapp
from app.config.settings import settings
from app.domain.exceptions import ConflictError, NotFoundError
from app.models.contract import BillingPeriodicity, ContractSignatureStatus
from app.models.message_template import TemplateKey
from app.repositories import (
    client_repository,
    contract_item_repository,
    contract_repository,
    equipment_repository,
    equipment_stock_repository,
    filial_repository,
)
from app.services import message_template_service

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)))

_PERIODICIDADE_LABELS = {
    BillingPeriodicity.UNICA: "única",
    BillingPeriodicity.MENSAL: "mensal",
    BillingPeriodicity.DIARIA: "diária",
    BillingPeriodicity.HORA: "por hora trabalhada",
}

_TEMPLATE_BY_TIPO = {
    "locacao": ("contract_locacao.html", "Contrato de Locação de Equipamentos", "LOCADORA", "LOCATÁRIA"),
    "servico": ("contract_servico.html", "Contrato de Prestação de Serviços", "PRESTADORA", "CONTRATANTE"),
}


def _formatar_valor(valor: Decimal | None) -> str:
    if valor is None:
        return "—"
    return f"R$ {valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _formatar_data(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def _valor_referencia_item(item, estoque, periodicidade: BillingPeriodicity) -> str:
    if item.valor_item is not None:
        return _formatar_valor(item.valor_item)
    if estoque is None:
        return "—"
    if periodicidade == BillingPeriodicity.DIARIA:
        return _formatar_valor(estoque.valor_diario)
    if periodicidade == BillingPeriodicity.MENSAL:
        return _formatar_valor(estoque.valor_mensal)
    if periodicidade == BillingPeriodicity.HORA:
        return _formatar_valor(estoque.valor_hora)
    return "—"


def generate_contract_pdf(db: Session, contract_id: int) -> bytes:
    contract = contract_repository.get(db, contract_id)
    if contract is None:
        raise NotFoundError(f"Contrato {contract_id} não encontrado")

    cliente = client_repository.get(db, contract.cliente_id)
    itens = contract_item_repository.list_by_contrato(db, contract_id)

    itens_contexto = []
    for item in itens:
        equipamento = equipment_repository.get(db, item.equipamento_id)
        filial = filial_repository.get(db, item.filial_id)
        estoque = equipment_stock_repository.get(db, item.equipamento_id, item.filial_id)
        itens_contexto.append(
            {
                "equipamento_nome": equipamento.nome if equipamento else f"Equipamento #{item.equipamento_id}",
                "identificador": equipamento.identificador if equipamento else None,
                "filial_nome": filial.nome if filial else f"Filial #{item.filial_id}",
                "quantidade": item.quantidade,
                "valor_referencia": _valor_referencia_item(item, estoque, contract.periodicidade_cobranca),
            }
        )

    template_name, titulo, empresa_papel, cliente_papel = _TEMPLATE_BY_TIPO[contract.tipo.value]
    template = _env.get_template(template_name)
    html = template.render(
        titulo=titulo,
        empresa_papel=empresa_papel,
        cliente_papel=cliente_papel,
        gerado_em=_formatar_data(datetime.now().date()),
        empresa={
            "nome": settings.company_name,
            "documento": settings.company_document,
            "endereco": settings.company_address,
        },
        cliente={
            "nome": cliente.nome if cliente else "Cliente não encontrado",
            "documento": cliente.documento if cliente else "—",
            "endereco": cliente.endereco if cliente else None,
            "tipo": cliente.tipo.value if cliente else "PF",
        },
        contrato={
            "id": contract.id,
            "data_inicio": _formatar_data(contract.data_inicio),
            "data_fim": _formatar_data(contract.data_fim),
            "valor_total": _formatar_valor(contract.valor_total) if contract.valor_total else None,
        },
        periodicidade_label=_PERIODICIDADE_LABELS[contract.periodicidade_cobranca],
        multa_atraso_percentual=f"{settings.late_fee_percentage:g}%",
        itens=itens_contexto,
    )

    output = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=output)
    if result.err:
        raise RuntimeError("Falha ao gerar PDF do contrato")
    return output.getvalue()


def send_contract_whatsapp(db: Session, contract_id: int) -> None:
    contract = contract_repository.get(db, contract_id)
    if contract is None:
        raise NotFoundError(f"Contrato {contract_id} não encontrado")

    cliente = client_repository.get(db, contract.cliente_id)
    if cliente is None or not cliente.telefone:
        raise ConflictError("Cliente não tem telefone cadastrado para envio via WhatsApp")

    pdf_bytes = generate_contract_pdf(db, contract_id)
    _, titulo, _, _ = _TEMPLATE_BY_TIPO[contract.tipo.value]
    legenda = message_template_service.render(
        db,
        TemplateKey.CONTRATO_ASSINATURA,
        cliente_nome=cliente.nome,
        tipo_contrato=titulo.lower(),
        contrato_id=str(contract.id),
    )
    # Opções fixas (não vem do template editável) — o webhook em
    # contract_signature_service só reconhece "1" ou "2" como resposta, então
    # o texto das opções não pode ser alterado livremente pelo admin em
    # Configurações (mudaria o que o cliente precisa digitar, não o parsing).
    mensagem_completa = (
        f"{legenda}\n\nPara continuar, responda com o número da opção:\n"
        f"1 - Aceito os termos e condições\n"
        f"2 - Não aceito os termos"
    )
    whatsapp.send_document(
        cliente.telefone,
        base64.b64encode(pdf_bytes).decode("ascii"),
        f"contrato_{contract.id}.pdf",
        mensagem_completa,
    )
    contract_repository.update(
        db,
        contract,
        {
            "assinatura_status": ContractSignatureStatus.AGUARDANDO_CONFIRMACAO,
            "assinatura_mensagem_enviada": mensagem_completa,
            "assinatura_enviada_em": datetime.now(),
            "assinatura_resposta_texto": None,
            "assinatura_confirmada_em": None,
            "assinatura_comprovante_key": None,
        },
    )
    db.commit()
