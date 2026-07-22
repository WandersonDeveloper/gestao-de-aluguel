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
| Equipamentos | `/equipment` | Filtros `?categoria_id=`, `?status=`, `?nome=`, `?filial_id=` (equipamentos com estoque na filial). `status` **não** é editável via `PATCH` — ver seção de equipamento abaixo. Cadastro é só catálogo (nome/categoria/marca/modelo/identificador/localização/observações) — quantidade e valores de locação ficam no sub-recurso `/equipment/{id}/estoque`, um por filial (ver abaixo e `regras-de-negocio.md`) |
| Fornecedores | `/suppliers` | Filtro `?nome=` |
| Filiais | `/filiais` | `POST`/`PATCH`/`DELETE` exigem **admin**; `GET` (lista/detalhe) aberto a qualquer papel. Exclusão bloqueada (409) se houver estoque de equipamento ou item de contrato vinculado |

Todos exigem apenas usuário autenticado (qualquer papel), exceto onde indicado.

## Equipamento — disponibilidade (Módulo 2)

- `POST /equipment/{id}/status` — transiciona o status do equipamento pela máquina de estado (ver regras de negócio). Corpo: `{"status": "...", "motivo": "..."}`. **Requer papel admin/operador.** Só é significativo para equipamento serializado — itens de estoque (mais de uma filial, ou quantidade > 1) ignoram o status.
- `GET /equipment/{id}/movements` — histórico de transições de status (auditoria).
- `POST /equipment/{id}/photos` — upload de foto (multipart `file`). **Requer papel admin/operador.**
- `GET /equipment/{id}/photos` — lista fotos com URL assinada (expira em 1h).
- `DELETE /equipment/{id}/photos/{key}` — remove uma foto. **Requer papel admin/operador.**

### Estoque por filial

- `GET /equipment/{id}/estoque` — lista todos os `EquipmentStock` (um por filial) desse equipamento. Aberto a qualquer papel.
- `PUT /equipment/{id}/estoque/{filial_id}` — cria ou atualiza (upsert) o estoque desse equipamento naquela filial. Corpo: `{"quantidade": N, "valor_diario"?, "valor_mensal"?, "valor_hora"?}`. **Requer papel admin/operador.** Reduzir `quantidade` abaixo do que já está reservado em algum período ativo falha com `409`.
- `DELETE /equipment/{id}/estoque/{filial_id}` — remove o estoque desse equipamento naquela filial. **Requer papel admin/operador.** Falha com `409` se houver reserva ativa de contrato ali, `404` se não existir estoque cadastrado nessa filial.
- `EquipmentRead` inclui `quantidade_total` (soma de todas as filiais, calculada) e `estoques: [{id, equipamento_id, filial_id, quantidade, valor_diario, valor_mensal, valor_hora}]`.

## Contratos (Módulo 3)

| Rota | Método | Papel exigido |
|---|---|---|
| `/contracts` | POST | admin/operador |
| `/contracts` | GET | qualquer papel |
| `/contracts/{id}` | GET | qualquer papel (retorna contrato + itens) |
| `/contracts/{id}/activate` | POST | admin/operador |
| `/contracts/{id}/baixa` | POST | admin/operador |
| `/contracts/{id}/extend` | POST | admin/operador |
| `/contracts/{id}/add-items` | POST | admin/operador |
| `/contracts/{id}/cancel` | POST | admin/operador |
| `/contracts/{id}/amendments` | GET | qualquer papel |
| `/contracts/{id}/documento` | GET | qualquer papel |
| `/contracts/{id}/send-whatsapp` | POST | admin/operador |
| `/contracts/{id}/comprovante-assinatura` | GET | qualquer papel (`404` se ainda não confirmado) |
| `/contracts/{id}/amendments/{amendment_id}/comprovante-assinatura` | GET | qualquer papel (`404` se aditivo ainda não confirmado) |
| `/contracts/{id}` | DELETE | **admin** (só contratos em `rascunho`) |
| `/contracts?status=&tipo=&cliente_id=&assinatura_status=` | GET | filtros combináveis, qualquer papel |

Detalhes de corpo de requisição:
- `POST /contracts`: `{cliente_id, data_inicio, data_fim?, itens: [{equipamento_id, filial_id, quantidade}], tipo?: "locacao"|"servico" (default "locacao"), periodicidade_cobranca?: "unica"|"mensal"|"diaria"|"hora", valor_total?, valor_recorrente?, observacoes?}`. Cada item reserva quantidade de um `EquipmentStock` específico — `filial_id` é obrigatório e precisa ter estoque cadastrado para esse equipamento (`404` se não tiver). Para equipamento serializado, `quantidade` deve ser `1`. `quantidade` pode ser qualquer valor que caiba no estoque disponível daquela filial no período — ver `regras-de-negocio.md` sobre reserva parcial e capacidade independente por filial. `tipo` é fixado na criação e usado depois por `GET /contracts/{id}/documento` para escolher o modelo do PDF — não é mais escolhido no download. `data_fim` omitido/`null` = contrato **em aberto** (sem término definido) — nesse caso `periodicidade_cobranca` não pode ser `"unica"` (`409`), e `valor_recorrente` (valor cobrado a cada período) substitui `valor_total` para fins de faturamento — ver `regras-de-negocio.md`.
- `POST /contracts/{id}/baixa`: `{item_ids: [...] | null, motivo?}` — `null` = baixa total. Baixa total falha com `409` se houver fatura `pendente`/`atrasada` no contrato (quite ou cancele antes); baixa parcial não tem essa restrição.
- `POST /contracts/{id}/extend`: `{nova_data_fim, motivo?}` — falha com 409 se a extensão não couber no estoque disponível no novo período, ou se o contrato for em aberto (não há data final para estender)
- `POST /contracts/{id}/add-items`: `{itens: [{equipamento_id, filial_id, quantidade}], condicao_cobranca_item?, data_vencimento_aditivo?, motivo?}` — adiciona equipamento a um contrato **já ativo** (aditivo), sem precisar criar um contrato novo. Só permitido com `status = ativo` (409 caso contrário — se o contrato estiver vencido, estenda primeiro). Mesma checagem de estoque disponível de `POST /contracts`. Os itens novos herdam o período restante do contrato (`data_inicio_item = hoje`, `data_fim_item = data_fim` do contrato), gravado também em `data_anterior`/`data_nova` do aditivo criado em `contract_amendments` (que também referencia os `ContractItem` criados via `amendment_id`, expostos em `itens` no `GET /contracts/{id}/amendments`). O valor do aditivo é **sempre calculado automaticamente** a partir do preço cadastrado no estoque do equipamento — nunca digitado manualmente. Para contratos `diaria`/`mensal`, usa a própria periodicidade do contrato (`condicao_cobranca_item` é ignorado). Para contratos `unica` (sem taxa recorrente própria), `condicao_cobranca_item` (`"diaria"` ou `"mensal"`) diz qual preço usar — se omitido, o item é adicionado sem gerar cobrança; `"hora"` não é aceito nesse caso (`409`, sem baixa automática por hora). Cobrança `hora` no próprio contrato nunca gera fatura na hora (entra na baixa). Quando há valor, gera uma fatura avulsa (vencendo hoje ou em `data_vencimento_aditivo`, se informado) e soma ao `valor_total` do contrato. Se o cliente tiver telefone cadastrado, envia confirmação via WhatsApp (opções "1"/"2", mesmo padrão da assinatura do contrato) — ver `regras-de-negocio.md`.
- `POST /contracts/{id}/cancel`: `{motivo?}`

Se `valor_total` for informado na criação (contrato de prazo fixo), a ativação do contrato (`POST /contracts/{id}/activate`) gera automaticamente as faturas em `invoices`, divididas conforme `periodicidade_cobranca` (ver Módulo 5). Sem `valor_total`, nenhuma fatura é gerada. Em contrato **em aberto** com `valor_recorrente` definido, a ativação gera só a fatura do primeiro período — as seguintes vêm do job diário `generate_recurring_invoices` (ver Scripts administrativos).

- `GET /contracts/{id}/documento` — gera e retorna um PDF (`application/pdf`) do contrato, preenchido com dados do cliente, itens, período e valor. O modelo usado (Contrato de Locação de Equipamentos ou Contrato de Prestação de Serviços) é definido pelo `tipo` salvo no contrato, não por parâmetro de query. Inclui cláusula de multa por atraso (mesmo `late_fee_percentage` das faturas). Ver `regras-de-negocio.md` para o aviso legal sobre o modelo ser genérico.
- `POST /contracts/{id}/send-whatsapp` — gera o mesmo PDF de `/documento` e envia via WhatsApp (Evolution API) para o telefone cadastrado do cliente, com uma legenda pedindo a assinatura seguida de duas opções fixas: `"1 - Aceito os termos e condições"` / `"2 - Não aceito os termos"`. Marca `assinatura_status` como `aguardando_confirmacao`. `409` se o cliente não tiver `telefone` cadastrado. Ver `regras-de-negocio.md` para detalhes da integração e do fluxo de confirmação.
- `GET /contracts/{id}/comprovante-assinatura` — retorna o PDF (`application/pdf`) do "Comprovante de Aceite Eletrônico", gerado automaticamente quando o cliente confirma pelo WhatsApp (ver webhook abaixo). `404` se `assinatura_status` ainda não for `confirmado`.

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
| `/invoices/{id}/send-whatsapp` | POST | admin/financeiro |
| `/invoices/{id}/payments` | POST | admin/financeiro |
| `/invoices/{id}/payments` | GET | qualquer papel |

- `POST /invoices/{id}/payments`: `{valor, forma_pagamento?, observacoes?}` — aceita pagamento parcial; a fatura só vira `paga` quando a soma dos pagamentos atinge o valor total.
- `POST /invoices/{id}/send-whatsapp` — envia uma mensagem de cobrança (valor, vencimento, e multa se `atrasada`) via WhatsApp (Evolution API) para o telefone cadastrado do cliente do contrato dessa fatura. `409` se o cliente não tiver `telefone` cadastrado.
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

## Configurações (`/settings`) — **admin only**

| Rota | Método | Descrição |
|---|---|---|
| `/settings/message-templates` | GET | Lista os templates de mensagem WhatsApp (`chave`, `conteudo`, `updated_at`) |
| `/settings/message-templates/{chave}` | PUT | Atualiza o texto de um template (`{conteudo}`). `409` se usar uma variável `{...}` não reconhecida para aquela `chave`, ou formatação inválida |
| `/settings/whatsapp/status` | GET | `{existe, estado}` — estado da instância na Evolution API (`open`/`connecting`/`close`/`null` se não existe) |
| `/settings/whatsapp/connect` | POST | Cria a instância (se não existir) ou busca um QR code novo; retorna `{estado, qrcode_base64}`. Se `META_WHATSAPP_TOKEN`/`META_WHATSAPP_NUMBER_ID` estiverem configurados no `.env`, cria a instância no modo API oficial (sem QR code) — ver `regras-de-negocio.md` |
| `/settings/whatsapp/disconnect` | POST | Desconecta a instância (`instance/logout`), para reparear com outro número |

`POST /settings/whatsapp/connect` também configura automaticamente, na Evolution API, o
webhook usado pela confirmação de assinatura de contrato (ver seção "Webhook" abaixo) — não
precisa de nenhum passo manual adicional.

`chave` é um de `cobranca_fatura` | `contrato_assinatura` | `aceite_confirmado` | `aceite_recusado`.
Variáveis disponíveis em cada template — usar exatamente esses nomes entre chaves, ex.
`{cliente_nome}`:
- `cobranca_fatura`: `cliente_nome`, `situacao`, `valor`, `vencimento`, `multa_texto`
- `contrato_assinatura`: `cliente_nome`, `tipo_contrato`, `contrato_id`
- `aceite_confirmado`: `cliente_nome`, `contrato_id`, `prazo_entrega` (enviado automaticamente quando o cliente responde "1")
- `aceite_recusado`: `cliente_nome`, `contrato_id` (enviado automaticamente quando o cliente responde "2")

`POST /invoices/{id}/send-whatsapp` e `POST /contracts/{id}/send-whatsapp` (ver seções acima)
usam esses templates para montar a mensagem — se a linha ainda não foi editada, cai no texto
default (mesmo texto que era hardcoded antes desta funcionalidade existir).

## Webhook (recebimento de mensagens do WhatsApp)

| Rota | Método | Auth |
|---|---|---|
| `/webhooks/whatsapp/{secret}` | POST | público — `secret` precisa bater com `WHATSAPP_WEBHOOK_SECRET`, senão `404` |

Configurado automaticamente pela Evolution API (ver `POST /settings/whatsapp/connect` acima) —
não é chamado pelo frontend, só pela própria Evolution API quando uma mensagem chega. Usado
hoje só para detectar a resposta do cliente ao pedido de assinatura: se o texto for
exatamente `"1"`, acha (por telefone, não por texto — ver `regras-de-negocio.md`) o contrato
`aguardando_confirmacao` daquele cliente, marca `confirmado`, gera o comprovante e responde
com a mensagem do template `aceite_confirmado`; se for `"2"`, marca `recusado` e responde com
o template `aceite_recusado`. Qualquer outro texto, ou nenhum contrato pendente pra aquele
telefone, é ignorado silenciosamente — sempre responde `200 {"status": "ok"}`.

## Scripts administrativos (fora da API HTTP)

- `python -m app.scripts.seed_admin` — cria o usuário admin inicial
- `python -m app.scripts.mark_expired_contracts` — job diário que marca contratos vencidos (ver README para agendamento via cron)
- `python -m app.scripts.mark_overdue_invoices` — job diário que marca faturas pendentes vencidas como `atrasada` e aplica a multa configurada (`late_fee_percentage`, padrão 2%)
- `python -m app.scripts.generate_recurring_invoices` — job diário que gera a próxima fatura de contratos **em aberto** (sem data final) com `valor_recorrente` definido, assim que o período anterior vence (ver `regras-de-negocio.md`)
