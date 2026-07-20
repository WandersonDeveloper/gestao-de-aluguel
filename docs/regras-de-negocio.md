# Regras de negócio

Este documento registra as decisões de negócio tomadas durante a implementação — inclusive as que o `plano-sistema-alugueis.md` deixava como "regra a decidir". É o complemento vivo daquele plano: o plano descreve a intenção original, este documento descreve o que foi efetivamente implementado e por quê.

## Máquinas de estado

### Equipamento (`app/domain/equipment_state.py`)

```
disponível → reservado → alugado → disponível
    ↑                        ↓
    └──────── manutenção ←───┘
```

- Transição só acontece via `POST /equipment/{id}/status` (nunca via `PATCH` genérico).
- Toda transição gera um registro em `inventory_movements` (usuário, data, motivo) — auditoria obrigatória.
- `manutenção → alugado` nunca é permitido diretamente.

### Contrato (`app/domain/contract_state.py`)

```
rascunho → ativo → encerrado
              ↓
           vencido → encerrado / cancelado
              ↓
           cancelado
```

- `vencido → ativo` é permitido: uma extensão de vigência que empurra `data_fim` para o futuro reativa o contrato.
- Extensão de contrato **não** é uma transição de status — só altera `data_fim` e gera um registro em `contract_amendments`.

### Ordem de serviço (`app/domain/service_order_state.py`)

```
aberta → em_andamento → concluída
   ↓
cancelada
```

### Fatura (`app/domain/invoice_state.py`)

```
pendente → paga
    ↓
 atrasada → paga / cancelada
```

- `pendente → atrasada`: job diário (`mark_overdue_invoices`), quando `data_vencimento < hoje`. Aplica uma multa de `late_fee_percentage` (padrão 2%, `app/config/settings.py`) sobre o valor da fatura, **uma única vez** — não há cálculo de juros compostos por dia de atraso.
- `pendente/atrasada → paga`: quando a soma dos pagamentos registrados atinge o valor da fatura. Pagamento parcial não muda o status (o modelo não tem um estado "parcialmente paga", conforme seção 4.4 do plano).
- `pendente/atrasada → cancelada`: manual, ou automático quando o contrato é cancelado (ver abaixo).

## Reserva de equipamento e conflito de datas

Um equipamento não pode ter dois itens de contrato **ativos** (não devolvidos) com períodos sobrepostos. Isso é garantido por uma `EXCLUDE CONSTRAINT` no PostgreSQL (`contract_items_no_overlap`, usando `daterange` + `gist`), não apenas por validação de aplicação — é a garantia central que motivou a escolha de Postgres em vez de MongoDB (ver seção 2 do plano).

## Decisões sobre pontos que o plano deixava em aberto

O plano (seção 5.4) marcava como "regra a decidir" o que acontece quando uma OS é aberta para um equipamento. Decisão tomada:

- **Abrir uma OS não move o equipamento para `manutenção` automaticamente.** Isso continua sendo uma ação manual e separada via `POST /equipment/{id}/status`. Motivo: nem toda OS aberta justifica tirar o equipamento de operação imediatamente (ex.: uma preventiva agendada para daqui a duas semanas).
- **Concluir ou cancelar uma OS libera o equipamento de volta para `disponível` automaticamente, se ele estava em `manutenção`.** Isso é um requisito explícito do plano (não ambíguo) e foi implementado em `service_order_service._release_equipment_if_in_maintenance`.

O plano (seção 5.3) também marcava como "regra a definir" se a baixa de contrato deveria validar a existência de OS aberta vinculada. **Não implementado** — dar baixa em um contrato não verifica OS abertas. Fica como ponto pendente caso o negócio precise dessa trava no futuro.

## Faturamento (Fase 5)

- Fatura só é gerada automaticamente **se o contrato tiver `valor_total` definido na criação**. Sem `valor_total`, a ativação não gera nenhuma fatura (não há como dividir um valor desconhecido).
- A divisão entre faturas segue `periodicidade_cobranca` do contrato (`unica`, `mensal`, `diaria`), dividindo `valor_total` em partes iguais (o resto de arredondamento fica na última fatura, para a soma bater exatamente com o total). O mesmo critério de divisão é aplicado entre os itens do contrato dentro de cada fatura (`invoice_items`).
- **Baixa de contrato não cancela faturas** — o cliente usou o equipamento, a cobrança segue normalmente. **Cancelamento de contrato cancela** as faturas ainda `pendente`/`atrasada` (faturas já `paga` não são afetadas) — isso segue exatamente a distinção que o plano já fazia na seção 4.2 entre baixa (gera cobrança) e cancelamento (normalmente não gera cobrança).
- Registrar pagamento e cancelar fatura exigem papel `admin` ou `financeiro` — **não** `operador`, que cuida da parte operacional (contratos/equipamentos/OS), não da parte financeira.

## Simplificações assumidas (não estavam no plano original)

- **Todos os itens de um contrato compartilham o mesmo período** (`data_inicio`/`data_fim` do contrato). O modelo de dados (`contract_items`) permite datas por item, mas a API de criação de contrato ainda não expõe isso — todo item criado recebe o mesmo período do contrato.
- **`maintenance_logs` não existe como tabela separada.** O plano (seção 7) listava `maintenance_logs` e `service_orders` como tabelas distintas; `service_orders` acumula esse papel sozinha (tipo preventiva/corretiva, descrição, diagnóstico em `observacoes`, datas de abertura/conclusão). Criar uma segunda tabela seria duplicar dado sem necessidade.
- **Cancelamento/baixa de item de contrato reutiliza o status `devolvido`.** O modelo só tem `ativo`/`devolvido` (seção 7 do plano); um item de um contrato cancelado antes de ser ativado também vira `devolvido`, mesmo nunca tendo sido fisicamente devolvido.

## RBAC (papéis: `admin`, `operador`, `financeiro`)

Regra geral: **ações operacionais** (que mudam o estado de um contrato, equipamento ou OS) exigem papel `admin` ou `operador`. **Leitura** (listagem/detalhe) e **cadastro básico** (clientes, categorias, equipamentos, fornecedores) ficam abertos a qualquer usuário autenticado, incluindo `financeiro` — que precisa dessas informações para cobrança, mas não deveria conseguir, por exemplo, encerrar um contrato ou colocar um equipamento em manutenção.

| Ação | Papel exigido |
|---|---|
| Criar/listar usuários | `admin` |
| CRUD de clientes/categorias/equipamentos/fornecedores | qualquer papel autenticado |
| Mudar status de equipamento, upload/remoção de foto | `admin`, `operador` |
| Criar/ativar/dar baixa/estender/cancelar contrato | `admin`, `operador` |
| Criar/iniciar/concluir/cancelar OS | `admin`, `operador` |
| Registrar pagamento, cancelar fatura | `admin`, `financeiro` |
| Leitura de contratos, OS, faturas, movimentações, aditivos, relatórios | qualquer papel autenticado |

Isso implementa por completo a divisão de papéis prevista na seção 11 do plano: `operador` cuida do fluxo operacional (contrato/equipamento/OS), `financeiro` cuida da cobrança, `admin` pode tudo. O plano mencionava "aplicar desconto" como ação restrita — não existe um desconto explícito hoje; o mais próximo é o `valor_total` livre definido na criação do contrato (que já exige `admin`/`operador`, os únicos que criam contrato).

## Exclusões e integridade referencial

Um equipamento **não pode ser excluído** se tiver:
- histórico de movimentação (`inventory_movements`);
- item de contrato vinculado, mesmo de contrato já encerrado (`contract_items`);
- ordem de serviço vinculada (`service_orders`).

Uma categoria de equipamento não pode ser excluída se algum equipamento ainda pertencer a ela. Em todos os casos a API responde `409 Conflict` com uma mensagem explicando o motivo, em vez de deixar a constraint de FK do banco estourar como erro 500.

## Object storage (fotos de equipamento)

Fotos são armazenadas em um bucket S3-compatível (MinIO em desenvolvimento), nunca como binário no banco — `equipment.fotos` guarda só uma lista de chaves. A URL de leitura é gerada sob demanda (presigned URL, expira em 1h), nunca persistida.
