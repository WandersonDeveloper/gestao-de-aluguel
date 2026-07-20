# API — Referência

Documentação viva e completa (schemas, exemplos de request/response) fica em `/docs` (Swagger) e `/redoc`, gerados automaticamente pelo FastAPI. Este documento é um índice de navegação e registra decisões de design que não aparecem no OpenAPI (RBAC, efeitos colaterais entre módulos).

Base URL: `http://localhost:8000/api`

## Autenticação

Todas as rotas exigem `Authorization: Bearer <token>`, exceto `POST /auth/login` e `GET /health`.

| Rota | Método | Auth | Descrição |
|---|---|---|---|
| `/auth/login` | POST | público | Recebe `email`+`senha`, retorna JWT |
| `/users/me` | GET | qualquer papel | Dados do usuário autenticado |
| `/users` | POST, GET | **admin** | Criar/listar usuários |

RBAC — três papéis: `admin`, `operador`, `financeiro` (ver `regras-de-negocio.md` para a matriz completa de permissões).

## Cadastros (Módulo 1)

CRUD padrão (`POST` cria, `GET` lista/detalha, `PATCH` atualiza, `DELETE` remove) para:

| Recurso | Prefixo | Observações |
|---|---|---|
| Clientes | `/clients` | Filtro `?nome=` |
| Categorias de equipamento | `/equipment-categories` | — |
| Equipamentos | `/equipment` | Filtros `?categoria_id=`, `?status=`, `?nome=`. `status` **não** é editável via `PATCH` — ver seção de equipamento abaixo |
| Fornecedores | `/suppliers` | Filtro `?nome=` |

Todos exigem apenas usuário autenticado (qualquer papel), exceto onde indicado.

## Equipamento — disponibilidade (Módulo 2)

- `POST /equipment/{id}/status` — transiciona o status do equipamento pela máquina de estado (ver regras de negócio). Corpo: `{"status": "...", "motivo": "..."}`. **Requer papel admin/operador.**
- `GET /equipment/{id}/movements` — histórico de transições de status (auditoria).
- `POST /equipment/{id}/photos` — upload de foto (multipart `file`). **Requer papel admin/operador.**
- `GET /equipment/{id}/photos` — lista fotos com URL assinada (expira em 1h).
- `DELETE /equipment/{id}/photos/{key}` — remove uma foto. **Requer papel admin/operador.**

## Contratos (Módulo 3)

| Rota | Método | Papel exigido |
|---|---|---|
| `/contracts` | POST | admin/operador |
| `/contracts` | GET | qualquer papel |
| `/contracts/{id}` | GET | qualquer papel (retorna contrato + itens) |
| `/contracts/{id}/activate` | POST | admin/operador |
| `/contracts/{id}/baixa` | POST | admin/operador |
| `/contracts/{id}/extend` | POST | admin/operador |
| `/contracts/{id}/cancel` | POST | admin/operador |
| `/contracts/{id}/amendments` | GET | qualquer papel |

Detalhes de corpo de requisição:
- `POST /contracts`: `{cliente_id, data_inicio, data_fim, equipamento_ids: [...], periodicidade_cobranca?: "unica"|"mensal"|"diaria", valor_total?, observacoes?}`
- `POST /contracts/{id}/baixa`: `{item_ids: [...] | null, motivo?}` — `null` = baixa total
- `POST /contracts/{id}/extend`: `{nova_data_fim, motivo?}`
- `POST /contracts/{id}/cancel`: `{motivo?}`

Se `valor_total` for informado na criação, a ativação do contrato (`POST /contracts/{id}/activate`) gera automaticamente as faturas em `invoices`, divididas conforme `periodicidade_cobranca` (ver Módulo 5). Sem `valor_total`, nenhuma fatura é gerada.

## Ordens de serviço (Módulo 4)

| Rota | Método | Papel exigido |
|---|---|---|
| `/service-orders` | POST | admin/operador |
| `/service-orders` | GET | qualquer papel (filtros `?equipamento_id=`, `?contrato_id=`, `?status=`) |
| `/service-orders/{id}` | GET | qualquer papel |
| `/service-orders/{id}/start` | POST | admin/operador |
| `/service-orders/{id}/complete` | POST | admin/operador |
| `/service-orders/{id}/cancel` | POST | admin/operador |

`complete`/`cancel` recebem `{observacoes?}` e liberam automaticamente o equipamento (volta a `disponivel`) se ele estava em `manutencao`.

## Financeiro (Módulo 5)

| Rota | Método | Papel exigido |
|---|---|---|
| `/invoices` | GET | qualquer papel (filtros `?contrato_id=`, `?status=`) |
| `/invoices/{id}` | GET | qualquer papel |
| `/invoices/{id}/items` | GET | qualquer papel |
| `/invoices/{id}/cancel` | POST | admin/financeiro |
| `/invoices/{id}/payments` | POST | admin/financeiro |
| `/invoices/{id}/payments` | GET | qualquer papel |

- `POST /invoices/{id}/payments`: `{valor, forma_pagamento?, observacoes?}` — aceita pagamento parcial; a fatura só vira `paga` quando a soma dos pagamentos atinge o valor total.
- Faturas são geradas automaticamente na ativação do contrato (ver seção de Contratos acima) — não há endpoint para criar fatura manualmente.
- Cancelar um contrato (`POST /contracts/{id}/cancel`) cancela automaticamente as faturas ainda `pendente`/`atrasada` desse contrato. Dar baixa (`/baixa`) **não** cancela faturas — a cobrança continua normalmente.

### Relatórios

| Rota | Descrição |
|---|---|
| `GET /reports/rentals?data_inicio=&data_fim=` | Contagem de contratos por status + valor total contratado no período |
| `GET /reports/most-rented-equipment?limit=` | Equipamentos mais alugados (por número de itens de contrato) |
| `GET /reports/overdue-invoices` | Faturas `atrasada` agrupadas por cliente |
| `GET /reports/dashboard` | KPIs gerais: equipamentos por status, contratos ativos/vencidos, OS abertas, inadimplência, receita do mês |

Todas as rotas de relatório exigem apenas usuário autenticado (qualquer papel).

## Scripts administrativos (fora da API HTTP)

- `python -m app.scripts.seed_admin` — cria o usuário admin inicial
- `python -m app.scripts.mark_expired_contracts` — job diário que marca contratos vencidos (ver README para agendamento via cron)
- `python -m app.scripts.mark_overdue_invoices` — job diário que marca faturas pendentes vencidas como `atrasada` e aplica a multa configurada (`late_fee_percentage`, padrão 2%)
