"""Popula o banco com dados de demonstracao (clientes, equipamentos, fornecedores,
contratos em varios estagios e ordens de servico) para testar a interface manualmente.

Uso: python -m app.scripts.seed_demo_data
"""

from datetime import date, timedelta
from decimal import Decimal

from app.config.database import SessionLocal
from app.models.equipment import EquipmentStatus
from app.repositories import (
    client_repository,
    equipment_category_repository,
    equipment_repository,
    filial_repository,
    supplier_repository,
    user_repository,
)
from app.schemas.client import ClientCreate
from app.schemas.contract import ContractCreate, ContractItemRequest
from app.schemas.equipment import EquipmentCreate
from app.schemas.equipment_category import EquipmentCategoryCreate
from app.schemas.equipment_stock import EquipmentStockUpsert
from app.schemas.filial import FilialCreate
from app.schemas.inventory_movement import EquipmentStatusChange
from app.schemas.payment import PaymentCreate
from app.schemas.service_order import ServiceOrderCreate
from app.schemas.supplier import SupplierCreate
from app.services import (
    client_service,
    contract_service,
    equipment_category_service,
    equipment_service,
    filial_service,
    invoice_service,
    payment_service,
    service_order_service,
    supplier_service,
)


def get_or_create_client(db, data: ClientCreate):
    existing = client_repository.get_by_documento(db, data.documento)
    if existing:
        return existing
    return client_service.create_client(db, data)


def get_or_create_supplier(db, data: SupplierCreate):
    existing = supplier_repository.get_by_documento(db, data.documento)
    if existing:
        return existing
    return supplier_service.create_supplier(db, data)


def get_or_create_category(db, nome: str, descricao: str | None = None):
    existing = equipment_category_repository.get_by_nome(db, nome)
    if existing:
        return existing
    return equipment_category_service.create_category(db, EquipmentCategoryCreate(nome=nome, descricao=descricao))


def get_or_create_filial(db, nome: str, endereco: str | None = None):
    existing = filial_repository.get_by_nome(db, nome)
    if existing:
        return existing
    return filial_service.create_filial(db, FilialCreate(nome=nome, endereco=endereco))


def get_or_create_equipment(db, data: EquipmentCreate):
    existing = equipment_repository.get_by_identificador(db, data.identificador)
    if existing:
        return existing
    return equipment_service.create_equipment(db, data)


def ensure_stock(
    db,
    equipment,
    filial_id: int,
    quantidade: int,
    valor_diario: Decimal | None = None,
    valor_mensal: Decimal | None = None,
    valor_hora: Decimal | None = None,
) -> None:
    equipment_service.set_estoque(
        db,
        equipment.id,
        filial_id,
        EquipmentStockUpsert(
            quantidade=quantidade, valor_diario=valor_diario, valor_mensal=valor_mensal, valor_hora=valor_hora
        ),
    )


def run() -> None:
    db = SessionLocal()
    try:
        admin = user_repository.get_by_email(db, "admin@alugueis.com")
        if admin is None:
            candidates = user_repository.list_all(db, limit=1)
            admin = candidates[0] if candidates else None
        if admin is None:
            print("Nenhum usuário encontrado — rode antes: python -m app.scripts.seed_admin")
            return
        usuario_id = admin.id

        # --- Filiais ---
        filial_matriz = get_or_create_filial(db, "Matriz - São Paulo", endereco="Av. das Nações, 1200 - São Paulo/SP")
        filial_campinas = get_or_create_filial(db, "Filial Campinas", endereco="Rod. Anhanguera, km 95 - Campinas/SP")

        # --- Categorias ---
        cat_escavadeiras = get_or_create_category(db, "Escavadeiras e Retroescavadeiras")
        cat_betoneiras = get_or_create_category(db, "Betoneiras")
        cat_andaimes = get_or_create_category(db, "Andaimes e Estruturas")
        cat_geradores = get_or_create_category(db, "Geradores")
        cat_ferramentas = get_or_create_category(db, "Ferramentas e Pequenos Equipamentos")

        # --- Equipamentos (cadastro único; quantidade e valores ficam por filial) ---
        escavadeira = get_or_create_equipment(
            db,
            EquipmentCreate(
                nome="Escavadeira Hidráulica CAT 320",
                categoria_id=cat_escavadeiras.id,
                marca="Caterpillar",
                modelo="320",
                identificador="ESC-001",
                localizacao="Pátio Central",
            ),
        )
        ensure_stock(db, escavadeira, filial_matriz.id, quantidade=1, valor_diario=Decimal("850.00"), valor_mensal=Decimal("18000.00"))

        retroescavadeira = get_or_create_equipment(
            db,
            EquipmentCreate(
                nome="Retroescavadeira JCB 3CX",
                categoria_id=cat_escavadeiras.id,
                marca="JCB",
                modelo="3CX",
                identificador="ESC-002",
                localizacao="Pátio Central",
            ),
        )
        ensure_stock(db, retroescavadeira, filial_matriz.id, quantidade=1, valor_diario=Decimal("650.00"), valor_mensal=Decimal("14000.00"))

        betoneira_400 = get_or_create_equipment(
            db,
            EquipmentCreate(
                nome="Betoneira 400L",
                categoria_id=cat_betoneiras.id,
                marca="Menegotti",
                modelo="CM400",
                identificador="BET-001",
                localizacao="Depósito 2",
            ),
        )
        ensure_stock(db, betoneira_400, filial_campinas.id, quantidade=1, valor_diario=Decimal("90.00"), valor_mensal=Decimal("1800.00"))

        betoneira_600 = get_or_create_equipment(
            db,
            EquipmentCreate(
                nome="Betoneira 600L",
                categoria_id=cat_betoneiras.id,
                marca="Menegotti",
                modelo="CM600",
                identificador="BET-002",
                localizacao="Depósito 2",
            ),
        )
        ensure_stock(db, betoneira_600, filial_campinas.id, quantidade=1, valor_diario=Decimal("120.00"), valor_mensal=Decimal("2400.00"))

        # Andaime: mesmo equipamento, estoque dividido entre as duas filiais, cada
        # uma com sua própria quantidade e valores — demonstra reserva parcial e
        # preços diferentes por filial.
        andaime = get_or_create_equipment(
            db,
            EquipmentCreate(
                nome="Andaime Tubular 2m",
                categoria_id=cat_andaimes.id,
                marca="Mills",
                identificador="AND-001",
                localizacao="Depósito 1",
            ),
        )
        ensure_stock(db, andaime, filial_matriz.id, quantidade=8, valor_diario=Decimal("25.00"), valor_mensal=Decimal("450.00"))
        ensure_stock(db, andaime, filial_campinas.id, quantidade=4, valor_diario=Decimal("30.00"), valor_mensal=Decimal("500.00"))

        gerador = get_or_create_equipment(
            db,
            EquipmentCreate(
                nome="Gerador Diesel 50kVA",
                categoria_id=cat_geradores.id,
                marca="Stemac",
                modelo="SS50",
                identificador="GER-001",
                localizacao="Pátio Central",
            ),
        )
        ensure_stock(db, gerador, filial_matriz.id, quantidade=1, valor_diario=Decimal("300.00"), valor_mensal=Decimal("6000.00"))

        compactador = get_or_create_equipment(
            db,
            EquipmentCreate(
                nome="Compactador de Placa Wacker",
                categoria_id=cat_ferramentas.id,
                marca="Wacker Neuson",
                identificador="FER-001",
                localizacao="Depósito 1",
            ),
        )
        ensure_stock(db, compactador, filial_campinas.id, quantidade=1, valor_diario=Decimal("60.00"), valor_mensal=Decimal("1100.00"))

        # --- Clientes ---
        cliente_horizonte = get_or_create_client(
            db,
            ClientCreate(
                nome="Construtora Horizonte Ltda",
                tipo="PJ",
                documento="12.345.678/0001-90",
                telefone="11 4002-8922",
                email="contato@horizonteconstrutora.com.br",
                endereco="Av. das Nações, 1200 - São Paulo/SP",
            ),
        )
        cliente_joao = get_or_create_client(
            db,
            ClientCreate(
                nome="João Pedro Almeida",
                tipo="PF",
                documento="123.456.789-00",
                telefone="11 98888-7766",
                email="joaopedro.almeida@example.com",
            ),
        )
        cliente_reformas = get_or_create_client(
            db,
            ClientCreate(
                nome="Reformas Rápidas ME",
                tipo="PJ",
                documento="98.765.432/0001-10",
                telefone="11 3344-5566",
                email="financeiro@reformasrapidas.com.br",
            ),
        )

        # --- Fornecedores ---
        get_or_create_supplier(
            db,
            SupplierCreate(
                nome="Peças Pesadas Distribuidora",
                documento="11.222.333/0001-44",
                telefone="11 5000-1000",
                email="vendas@pecaspesadas.com.br",
            ),
        )
        get_or_create_supplier(
            db,
            SupplierCreate(
                nome="Manutenção Diesel Express",
                documento="55.666.777/0001-88",
                telefone="11 5000-2000",
                email="contato@dieselexpress.com.br",
            ),
        )

        # --- Contratos (só cria se ainda não existir nenhum para esses clientes) ---
        ja_tem_contratos = bool(
            contract_service.list_contracts(db, cliente_id=cliente_horizonte.id, limit=1)
        )
        if ja_tem_contratos:
            print("Contratos de demonstração já existem — pulando essa etapa.")
        else:
            hoje = date.today()

            # C1: reserva futura (equipamento fica "reservado" após ativar)
            c1 = contract_service.create_contract(
                db,
                ContractCreate(
                    cliente_id=cliente_horizonte.id,
                    data_inicio=hoje + timedelta(days=10),
                    data_fim=hoje + timedelta(days=30),
                    itens=[ContractItemRequest(equipamento_id=escavadeira.id, filial_id=filial_matriz.id, quantidade=1)],
                    periodicidade_cobranca="mensal",
                    valor_total=Decimal("15000.00"),
                    observacoes="Obra Horizonte - Fase 2",
                ),
            )
            contract_service.activate_contract(db, c1.id, usuario_id)

            # C2: contrato ativo, fatura pendente — de prestação de serviço (com operador),
            # para demonstrar a outra variante de documento gerado em PDF.
            c2 = contract_service.create_contract(
                db,
                ContractCreate(
                    cliente_id=cliente_joao.id,
                    data_inicio=hoje,
                    data_fim=hoje + timedelta(days=15),
                    itens=[ContractItemRequest(equipamento_id=betoneira_400.id, filial_id=filial_campinas.id, quantidade=1)],
                    tipo="servico",
                    periodicidade_cobranca="unica",
                    valor_total=Decimal("1200.00"),
                ),
            )
            contract_service.activate_contract(db, c2.id, usuario_id)

            # C3: contrato ativo com fatura já paga
            c3 = contract_service.create_contract(
                db,
                ContractCreate(
                    cliente_id=cliente_reformas.id,
                    data_inicio=hoje - timedelta(days=5),
                    data_fim=hoje + timedelta(days=10),
                    itens=[ContractItemRequest(equipamento_id=gerador.id, filial_id=filial_matriz.id, quantidade=1)],
                    periodicidade_cobranca="unica",
                    valor_total=Decimal("4500.00"),
                ),
            )
            contract_service.activate_contract(db, c3.id, usuario_id)
            fatura_c3 = invoice_service.list_invoices(db, contrato_id=c3.id)[0]
            payment_service.register_payment(
                db, fatura_c3.id, PaymentCreate(valor=Decimal("4500.00"), forma_pagamento="pix"), usuario_id
            )

            # C4: contrato vencido com fatura em atraso (+ multa aplicada). Reserva
            # parcial: 2 das 8 unidades do andaime na filial Matriz.
            c4 = contract_service.create_contract(
                db,
                ContractCreate(
                    cliente_id=cliente_horizonte.id,
                    data_inicio=hoje - timedelta(days=20),
                    data_fim=hoje - timedelta(days=5),
                    itens=[ContractItemRequest(equipamento_id=andaime.id, filial_id=filial_matriz.id, quantidade=2)],
                    periodicidade_cobranca="unica",
                    valor_total=Decimal("375.00"),
                ),
            )
            contract_service.activate_contract(db, c4.id, usuario_id)
            invoice_service.mark_overdue_invoices(db)
            contract_service.mark_expired_contracts(db)

            # C5: contrato encerrado (baixa total já feita)
            c5 = contract_service.create_contract(
                db,
                ContractCreate(
                    cliente_id=cliente_joao.id,
                    data_inicio=hoje - timedelta(days=30),
                    data_fim=hoje - timedelta(days=20),
                    itens=[ContractItemRequest(equipamento_id=retroescavadeira.id, filial_id=filial_matriz.id, quantidade=1)],
                ),
            )
            contract_service.activate_contract(db, c5.id, usuario_id)
            contract_service.mark_expired_contracts(db)
            contract_service.dar_baixa(db, c5.id, None, "Devolução ao final da obra", usuario_id)

            # C6: rascunho (nunca ativado)
            contract_service.create_contract(
                db,
                ContractCreate(
                    cliente_id=cliente_reformas.id,
                    data_inicio=hoje + timedelta(days=5),
                    data_fim=hoje + timedelta(days=12),
                    itens=[ContractItemRequest(equipamento_id=compactador.id, filial_id=filial_campinas.id, quantidade=1)],
                    valor_total=Decimal("400.00"),
                    observacoes="Aguardando confirmação do cliente",
                ),
            )

            print("Contratos de demonstração criados (rascunho, ativo, pago, atrasado, encerrado).")

        # --- Ordens de serviço ---
        if equipment_repository.get(db, betoneira_600.id).status != EquipmentStatus.MANUTENCAO:
            equipment_service.change_status(
                db,
                betoneira_600.id,
                EquipmentStatusChange(status=EquipmentStatus.MANUTENCAO, motivo="Manutenção preventiva programada"),
                usuario_id,
            )
            service_order_service.create_service_order(
                db,
                ServiceOrderCreate(
                    equipamento_id=betoneira_600.id,
                    tipo="corretiva",
                    descricao="Ruído estranho no motor durante a mistura",
                    prioridade="alta",
                ),
            )

            os_preventiva = service_order_service.create_service_order(
                db,
                ServiceOrderCreate(
                    equipamento_id=retroescavadeira.id,
                    tipo="preventiva",
                    descricao="Revisão das 500 horas",
                    prioridade="media",
                ),
            )
            service_order_service.start_service_order(db, os_preventiva.id)

            os_concluida = service_order_service.create_service_order(
                db,
                ServiceOrderCreate(
                    equipamento_id=compactador.id,
                    tipo="preventiva",
                    descricao="Checklist de segurança mensal",
                    prioridade="baixa",
                ),
            )
            service_order_service.start_service_order(db, os_concluida.id)
            service_order_service.complete_service_order(
                db, os_concluida.id, "Equipamento aprovado, sem pendências.", usuario_id
            )

            print("Ordens de serviço de demonstração criadas (aberta, em andamento, concluída).")
        else:
            print("Ordens de serviço de demonstração já existem — pulando essa etapa.")

        print("Seed de demonstração concluído com sucesso.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
