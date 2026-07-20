# Plano de desenvolvimento — Sistema de gestão de aluguéis de equipamentos

## 1. Objetivo do projeto

Criar um sistema genérico para controlar aluguel de equipamentos e máquinas, com possibilidade de ampliar para diferentes tipos de ativos, como:

- máquinas pesadas
- caçambas
- betoneiras
- andaimes
- pequenos equipamentos e ferramentas
- containers para construção

O sistema deve permitir:

- cadastro de clientes
- cadastro de equipamentos e categorias
- controle de estoque e disponibilidade (incluindo reservas futuras, não só status atual)
- criação de ordens de serviço
- emissão e controle de contratos de aluguel
- acompanhamento de prestação de serviço
- gestão de manutenção e devolução
- controle financeiro (cobrança, parcelas, atraso)

---

## 2. Visão geral da solução

### Stack definida

- **Frontend:** React
- **Backend:** Python com **FastAPI** — tipagem nativa (Pydantic), documentação OpenAPI automática, suporte assíncrono, boa opção para uma API REST nova.
- **Banco de dados:** **PostgreSQL** (não MongoDB — ver justificativa abaixo)
- **Armazenamento de arquivos:** object storage compatível com S3 (AWS S3, ou MinIO self-hosted) para fotos de equipamentos e anexos de contrato/OS. Não guardar binário no banco.
- **Autenticação:** JWT + controle de papéis (RBAC)
- **Estrutura de pastas:** modular, com camada de domínio isolada das regras de state machine

### Por que PostgreSQL em vez de MongoDB

O domínio do sistema é **fortemente relacional e transacional**:

- um equipamento não pode estar em dois contratos ativos ao mesmo tempo → isso é uma constraint de integridade, não uma regra de aplicação;
- contratos têm itens, faturas, pagamentos e aditivos com relações de chave estrangeira bem definidas;
- reservas de datas precisam de checagem de sobreposição (overlap) com garantia de atomicidade — bancos relacionais resolvem isso nativamente com transactions e constraints (`EXCLUDE USING gist` para ranges de data, por exemplo); em MongoDB isso exigiria lógica manual e transactions multi-documento, mais lentas e mais propensas a bugs de concorrência.

A única razão para considerar MongoDB era a "flexibilidade de atributos variáveis dos equipamentos" — isso é resolvido em PostgreSQL com uma coluna `JSONB` (`equipment.atributos_extra`), mantendo o restante do schema relacional e com constraints reais.

### Arquitetura proposta

- Frontend React para telas de cadastro, listagem, contratos, dashboards e relatórios
- Backend FastAPI com endpoints REST para:
  - cadastro de entidades
  - regras de negócio e máquinas de estado (equipamento, contrato, OS, fatura)
  - validações (Pydantic schemas)
  - integração com PostgreSQL (SQLAlchemy + Alembic para migrations)
  - integração com object storage para arquivos
- PostgreSQL como fonte única da verdade, com JSONB apenas para atributos variáveis de equipamento

---

## 3. Conceito de negócio

O sistema deve ser pensado como uma plataforma de gestão operacional e comercial para aluguel de ativos. A ideia é permitir que o gestor tenha visão clara de:

- quais equipamentos existem
- qual está disponível, reservado, alugado ou em manutenção
- quais contratos estão ativos, vencidos ou encerrados
- quais ordens de serviço foram abertas
- qual o status financeiro de cada contrato (em dia, atrasado, quitado)
- qual o status de cada item no ciclo de locação, desde a reserva até a devolução

---

## 4. Máquinas de estado

Definir estados e transições explicitamente evita o bug mais comum desse tipo de sistema: equipamento "alugado" sem contrato vinculado, ou contrato "ativo" com todos os itens devolvidos.

### 4.1 Equipamento

```
disponível → reservado → alugado → disponível
    ↑                        ↓
    └──────── manutenção ←───┘
```

Regras de transição:

- `disponível → reservado`: ao vincular o equipamento a um contrato com data de início futura, ou no momento da criação do contrato.
- `reservado → alugado`: na data de início do contrato (retirada confirmada).
- `alugado → disponível`: na devolução (baixa total ou baixa parcial do item).
- `alugado → manutenção`: abertura de OS corretiva durante a locação (equipamento sai do contrato ou fica sinalizado, dependendo da regra de negócio a definir).
- `disponível → manutenção`: manutenção preventiva agendada.
- `manutenção → disponível`: conclusão da OS.
- Nunca permitir `manutenção → alugado` diretamente — sempre passa por `disponível`.

### 4.2 Contrato

```
rascunho → ativo → encerrado
              ↓
           vencido → encerrado / cancelado
              ↓
           cancelado
```

Regras de transição:

- `rascunho → ativo`: todos os itens têm equipamento vinculado e disponível, cliente e datas validados.
- `ativo → vencido`: job diário verifica `data_fim < hoje` e contrato ainda não encerrado.
- `ativo/vencido → encerrado` (baixa total): libera todos os equipamentos vinculados.
- `ativo → encerrado` parcial (baixa parcial de itens): contrato permanece `ativo` se ainda houver itens não baixados; só migra para `encerrado` quando o último item for baixado.
- `ativo/vencido → cancelado`: cancelamento administrativo (ex.: erro de cadastro), difere de baixa porque normalmente não gera cobrança.
- extensão de contrato: não é uma transição de status — cria um registro em `contract_amendments` alterando `data_fim`, mantendo o contrato em `ativo` e preservando o histórico original.

### 4.3 Ordem de serviço (OS)

```
aberta → em_andamento → concluída
   ↓
cancelada
```

### 4.4 Fatura / parcela

```
pendente → paga
    ↓
 atrasada → paga / cancelada
```

---

## 5. Fluxos detalhados

### 5.1 Fluxo de cadastro e disponibilização de equipamento

1. Usuário cadastra categoria (se ainda não existir).
2. Usuário cadastra equipamento vinculado à categoria, com valor diário/mensal, fotos (upload para object storage) e atributos extras (JSONB) específicos da categoria.
3. Equipamento entra no sistema com status `disponível`.
4. Equipamento aparece nas buscas de disponibilidade para novos contratos.

### 5.2 Fluxo de criação de contrato (com checagem de conflito)

1. Usuário seleciona cliente (ou cadastra um novo).
2. Usuário seleciona equipamento(s) e período desejado (`data_inicio`, `data_fim`).
3. Backend verifica, por equipamento, se já existe reserva/contrato ativo com **sobreposição de datas** — via constraint de exclusão no banco (`EXCLUDE USING gist` sobre `daterange`) mais validação na camada de serviço para retornar erro amigável.
4. Se não houver conflito: cria contrato em `rascunho`, com itens vinculados.
5. Ao confirmar o contrato (assinatura/retirada), equipamento(s) passam para `reservado` (se início futuro) ou `alugado` (se início é hoje), e contrato passa para `ativo`.
6. Sistema gera a primeira fatura/parcela conforme condições comerciais definidas no contrato.

### 5.3 Fluxo de devolução, baixa e extensão

**Baixa total:**
1. Usuário abre o contrato ativo e aciona "encerrar contrato".
2. Sistema valida que não há pendências bloqueantes (ex.: OS aberta crítica — regra a definir).
3. Todos os itens são marcados como devolvidos; equipamentos voltam para `disponível` (ou `manutenção`, se o usuário sinalizar problema na devolução).
4. Contrato passa para `encerrado`; histórico de baixa registrado com data, usuário responsável e observações.

**Baixa parcial:**
1. Usuário seleciona um subconjunto dos itens do contrato para devolver.
2. Os equipamentos desses itens voltam para `disponível`/`manutenção`; os demais itens continuam `alugado`.
3. Contrato permanece `ativo` até que todos os itens tenham sido baixados.
4. Valor da fatura é recalculado proporcionalmente, se aplicável.

**Extensão:**
1. Usuário solicita nova data final para o contrato (ou para itens específicos).
2. Sistema cria um registro em `contract_amendments` com a data anterior, a nova data e o motivo.
3. `data_fim` do contrato é atualizada; equipamentos envolvidos permanecem `alugado`.
4. Nova fatura/parcela é gerada para o período estendido, se aplicável.

### 5.4 Fluxo de ordem de serviço e manutenção

1. OS pode ser aberta a partir de um equipamento (manutenção preventiva agendada) ou a partir de um contrato ativo (problema reportado durante a locação).
2. Ao abrir OS corretiva vinculada a um contrato ativo, o sistema sinaliza o equipamento (regra a decidir: bloqueia o item do contrato ou mantém alugado até decisão manual).
3. Técnico atualiza status da OS (`em_andamento` → `concluída`), registrando diagnóstico e serviço realizado.
4. Conclusão da OS libera o equipamento de volta para `disponível`, se estava em `manutenção`.
5. Histórico de manutenção fica vinculado ao equipamento para consulta futura (ex.: equipamento com muitas OS = candidato a substituição).

### 5.5 Fluxo financeiro

1. Cada contrato gera uma ou mais faturas/parcelas conforme a periodicidade definida (diária, mensal, única).
2. Cada fatura pode cobrir um ou mais itens do contrato — relação explícita em `invoice_items`.
3. Pagamento registrado baixa a fatura (total ou parcial).
4. Job diário verifica faturas com `data_vencimento < hoje` e status `pendente` → atualiza para `atrasada` e aplica multa/juros conforme regra configurada.
5. Relatórios de inadimplência consultam faturas `atrasada` agrupadas por cliente/contrato.
6. (Evolução futura) Emissão de NFS-e integrada a um provedor de notas fiscais — não é escopo do MVP, mas o modelo de fatura já deve prever campo para número/status de nota fiscal, para não travar a arquitetura depois.

---

## 6. Módulos iniciais do sistema

### Módulo 1 — Cadastros base

Objetivo: criar a base estrutural do sistema.

Entidades principais:

- Usuários (com papel/RBAC)
- Clientes
- Categorias de equipamentos
- Equipamentos
- Fornecedores
- Unidades/filiais (se necessário)

Funcionalidades:

- CRUD de clientes
- CRUD de categorias
- CRUD de equipamentos
- definição de status do equipamento (ver máquina de estado, seção 4.1)
- associação de fotos (object storage) e observações

### Módulo 2 — Controle de estoque e disponibilidade

Objetivo: controlar o estado operacional dos equipamentos.

Funcionalidades:

- disponibilidade por equipamento, incluindo reservas futuras
- status conforme máquina de estado (4.1)
- histórico de movimentação
- controle de entrada e saída
- reserva de equipamento para contrato, com checagem de conflito de datas (5.2)

### Módulo 3 — Contratos de aluguel

Objetivo: formalizar a locação.

Entidades principais:

- Contrato
- Itens do contrato
- Cliente
- Equipamentos vinculados
- Datas de início/fim
- Valor do aluguel
- Condições e observações
- Aditivos e alterações de vigência (`contract_amendments`)

Funcionalidades:

- criar contrato (fluxo 5.2)
- adicionar itens ao contrato
- controlar vigência conforme máquina de estado (4.2)
- encerrar ou prorrogar contrato (fluxo 5.3)
- associar equipamento a um contrato ativo
- registrar baixa total do contrato
- registrar baixa parcial de itens do contrato
- registrar extensão de contrato com novo prazo
- manter histórico de alterações e aditivos

### Módulo 4 — Prestação de serviço e ordens de serviço

Objetivo: registrar ocorrências e serviços relacionados ao equipamento.

Funcionalidades (fluxo 5.4):

- abrir ordem de serviço
- registrar problemas técnicos
- registrar manutenção preventiva ou corretiva
- vincular ordem de serviço a um equipamento ou contrato
- atualizar status da OS conforme máquina de estado (4.3)

### Módulo 5 — Financeiro e relatórios

Objetivo: dar visão comercial e operacional (fluxo 5.5).

Funcionalidades:

- geração de cobranças (faturas/parcelas)
- controle de parcelas e baixa de pagamento
- aplicação automática de multa/juros por atraso
- histórico de pagamentos
- relatórios de locação
- relatórios de equipamentos mais alugados
- relatórios de inadimplência

---

## 7. Modelo de dados (PostgreSQL)

### Tabelas principais

- users
- clients
- equipment_categories
- equipment
- suppliers
- contracts
- contract_items
- contract_amendments
- service_orders
- maintenance_logs
- inventory_movements
- invoices
- invoice_items
- payments

### Entidades principais

#### Equipamento (`equipment`)

Campos sugeridos:

- id
- nome
- categoria_id (FK)
- marca
- modelo
- placa_chassi_identificador (unique)
- status (enum: disponível, reservado, alugado, manutenção)
- valor_diario
- valor_mensal
- localização
- observações
- atributos_extra (JSONB — campos variáveis por categoria)
- fotos (referências para object storage, não binário)
- data_cadastro

#### Cliente (`clients`)

Campos sugeridos:

- id
- nome
- tipo (PF/PJ)
- documento (unique)
- telefone
- email
- endereço
- observações

#### Contrato (`contracts`)

Campos sugeridos:

- id
- cliente_id (FK)
- data_inicio
- data_fim
- status (enum: rascunho, ativo, vencido, encerrado, cancelado)
- valor_total
- observações

#### Item do contrato (`contract_items`)

- id
- contrato_id (FK)
- equipamento_id (FK)
- data_inicio_item
- data_fim_item
- status (ativo, devolvido)
- valor_item

#### Aditivo de contrato (`contract_amendments`)

- id
- contrato_id (FK)
- tipo (extensão, alteração de valor, outro)
- data_anterior
- data_nova
- motivo
- usuário_responsável
- data_registro

#### Ordem de serviço (`service_orders`)

Campos sugeridos:

- id
- equipamento_id (FK)
- contrato_id (FK, opcional)
- tipo (preventiva, corretiva)
- descrição
- prioridade
- status (aberta, em_andamento, concluída, cancelada)
- data_abertura
- data_conclusao

#### Fatura (`invoices`) / Parcela

- id
- contrato_id (FK)
- data_vencimento
- valor
- status (pendente, paga, atrasada, cancelada)
- multa_juros_aplicado
- numero_nota_fiscal (nullable, para evolução futura)

---

## 8. Estrutura inicial do projeto

### Backend

- app/
  - controllers/ (routers FastAPI)
  - services/ (regras de negócio, orquestração)
  - domain/ (máquinas de estado: equipment_state.py, contract_state.py, os_state.py)
  - repositories/ (acesso a dados, queries)
  - models/ (SQLAlchemy models)
  - schemas/ (Pydantic — validação de entrada/saída)
  - config/ (settings, conexão DB, object storage)
  - routes/
  - utils/
  - tests/ (unitários e de integração — cobertura obrigatória para domain/ e services/)

### Frontend

- src/
  - components/
  - pages/
  - routes/
  - services/
  - hooks/
  - context/
  - styles/

### Documentação

- docs/
  - plano-sistema-alugueis.md
  - api.md
  - regras-de-negocio.md

---

## 9. Fases de desenvolvimento

### Fase 0 — Base do projeto

Objetivo: preparar a estrutura inicial.

Entregáveis:

- configuração do repositório
- backend FastAPI com estrutura modular (controllers/services/domain/repositories)
- frontend React inicial
- conexão com PostgreSQL + Alembic para migrations
- autenticação básica (JWT) com papéis (admin, operador, financeiro)
- ambiente de desenvolvimento documentado (docker-compose com Postgres + backend + frontend)

### Fase 1 — Cadastros essenciais

Objetivo: criar a base de dados operacional.

Entregáveis:

- cadastro de clientes
- cadastro de categorias
- cadastro de equipamentos (com upload de fotos para object storage)
- listagem e filtros

### Fase 2 — Controle de estoque e disponibilidade

Objetivo: dar visão real do estado dos equipamentos.

Entregáveis:

- máquina de estado do equipamento implementada (4.1)
- controle de entrada e saída
- histórico de movimentações
- disponibilidade para locação com checagem de conflito de datas

### Fase 3 — Contratos e locação

Objetivo: implementar o núcleo do negócio.

Entregáveis:

- criação de contratos (fluxo 5.2)
- inclusão de itens no contrato
- vínculo com equipamentos
- controle de vigência (máquina de estado 4.2)
- baixa total, baixa parcial e extensão (fluxo 5.3)

### Fase 4 — Ordens de serviço e manutenção

Objetivo: gerenciar problemas e manutenção.

Entregáveis:

- abertura de OS
- máquina de estado da OS (4.3)
- histórico de manutenção
- vínculo com contratos e equipamentos

### Fase 5 — Financeiro e relatórios

Objetivo: dar controle comercial ao sistema.

Entregáveis:

- geração de fatura/parcelas (fluxo 5.5)
- job de verificação de atraso e aplicação de multa/juros
- controle de pagamentos
- relatórios básicos (locação, equipamentos mais alugados, inadimplência)
- dashboard executivo

### Fase 6 — Evolução e automação

Objetivo: crescer com o negócio.

Entregáveis:

- integrações externas (ex.: emissão de NFS-e)
- notificações (email/WhatsApp) de vencimento e devolução
- alertas de vencimento
- busca avançada
- exportação de dados

---

## 10. Estratégia recomendada para começar

O melhor caminho é começar com um MVP enxuto, focado no núcleo do processo de aluguel:

1. cadastrar clientes
2. cadastrar equipamentos
3. controlar status de disponibilidade (máquina de estado 4.1)
4. criar contrato de aluguel com checagem de conflito de datas (fluxo 5.2)
5. vincular equipamento ao contrato
6. registrar devolução (baixa total/parcial) e manutenção (fluxos 5.3 e 5.4)

Esse MVP já entrega valor real e depois pode evoluir com os módulos de financeiro, relatórios e automação.

---

## 11. Regras de negócio

- um equipamento só pode estar associado a um contrato ativo por vez — garantido por constraint no banco (`EXCLUDE USING gist` sobre range de datas), não apenas validação de aplicação
- um equipamento em manutenção não deve estar disponível para locação
- contratos devem ter status controlado: rascunho, ativo, vencido, encerrado, cancelado (máquina de estado 4.2)
- baixa parcial deve afetar apenas os itens selecionados, sem encerrar automaticamente o contrato inteiro
- baixa total deve encerrar o contrato e liberar todos os equipamentos vinculados
- extensão de contrato deve criar um registro em `contract_amendments` sem perder o histórico original, sem alterar o status do contrato
- ordens de serviço devem registrar a situação atual do equipamento
- o sistema deve permitir uma visão geral por cliente, equipamento e contrato
- controle de acesso por papel (RBAC): definir no mínimo `admin`, `operador` e `financeiro`, com permissões distintas para encerrar contrato, aplicar desconto e dar baixa em pagamento
- toda transição de estado (equipamento, contrato, OS, fatura) deve ser auditável: usuário responsável, data/hora e motivo, quando aplicável

---

## 12. Próximos passos

### Prioridade 1

Montar a base do projeto com:

- backend FastAPI com estrutura modular
- API REST inicial documentada (OpenAPI automático)
- conexão com PostgreSQL + Alembic
- frontend React inicial

### Prioridade 2

Implementar os cadastros base:

- clientes
- categorias
- equipamentos

### Prioridade 3

Implementar fluxo de contrato e disponibilidade, incluindo checagem de conflito de datas e máquinas de estado.

---

## 13. Recomendações finais

Para esse tipo de sistema, o mais importante é construir com uma arquitetura modular desde o início, com as regras de máquina de estado isoladas em uma camada de domínio (`domain/`) separada dos controllers. Isso evita retrabalho quando o sistema crescer e permite adicionar módulos sem quebrar a base.

A recomendação é seguir este caminho:

- base sólida primeiro (banco relacional com constraints reais, autenticação com papéis)
- cadastro e fluxo operacional depois, com máquinas de estado explícitas
- relatórios e financeiro na sequência
- cobertura de testes para as regras de domínio (máquinas de estado e checagem de conflito de datas) desde a Fase 2, não como item de última hora

Esse modelo é ideal para um sistema de aluguel de equipamentos que pode crescer com o tempo e atender diferentes tipos de ativos.
