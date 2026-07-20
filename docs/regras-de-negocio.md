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

## Reserva de equipamento e conflito de datas

Um equipamento não pode ter dois itens de contrato **ativos** (não devolvidos) com períodos sobrepostos. Isso é garantido por uma `EXCLUDE CONSTRAINT` no PostgreSQL (`contract_items_no_overlap`, usando `daterange` + `gist`), não apenas por validação de aplicação — é a garantia central que motivou a escolha de Postgres em vez de MongoDB (ver seção 2 do plano).

## Decisões sobre pontos que o plano deixava em aberto

O plano (seção 5.4) marcava como "regra a decidir" o que acontece quando uma OS é aberta para um equipamento. Decisão tomada:

- **Abrir uma OS não move o equipamento para `manutenção` automaticamente.** Isso continua sendo uma ação manual e separada via `POST /equipment/{id}/status`. Motivo: nem toda OS aberta justifica tirar o equipamento de operação imediatamente (ex.: uma preventiva agendada para daqui a duas semanas).
- **Concluir ou cancelar uma OS libera o equipamento de volta para `disponível` automaticamente, se ele estava em `manutenção`.** Isso é um requisito explícito do plano (não ambíguo) e foi implementado em `service_order_service._release_equipment_if_in_maintenance`.

O plano (seção 5.3) também marcava como "regra a definir" se a baixa de contrato deveria validar a existência de OS aberta vinculada. **Não implementado** — dar baixa em um contrato não verifica OS abertas. Fica como ponto pendente caso o negócio precise dessa trava no futuro.

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
| Leitura de contratos, OS, movimentações, aditivos | qualquer papel autenticado |

Este é o nível de granularidade implementado hoje. O plano (seção 11) também previa "aplicar desconto" e "dar baixa em pagamento" como ações restritas — essas não existem ainda porque o módulo financeiro (Fase 5) não foi implementado; quando existir, deve seguir o mesmo padrão (`require_roles` em `app/utils/deps.py`).

## Exclusões e integridade referencial

Um equipamento **não pode ser excluído** se tiver:
- histórico de movimentação (`inventory_movements`);
- item de contrato vinculado, mesmo de contrato já encerrado (`contract_items`);
- ordem de serviço vinculada (`service_orders`).

Uma categoria de equipamento não pode ser excluída se algum equipamento ainda pertencer a ela. Em todos os casos a API responde `409 Conflict` com uma mensagem explicando o motivo, em vez de deixar a constraint de FK do banco estourar como erro 500.

## Object storage (fotos de equipamento)

Fotos são armazenadas em um bucket S3-compatível (MinIO em desenvolvimento), nunca como binário no banco — `equipment.fotos` guarda só uma lista de chaves. A URL de leitura é gerada sob demanda (presigned URL, expira em 1h), nunca persistida.
