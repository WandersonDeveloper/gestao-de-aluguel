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

## Filiais e estoque por filial (`EquipmentStock`)

O plano original não previa múltiplas filiais nem controle de estoque — isso foi adicionado depois, a pedido explícito, e passou por duas iterações:

1. Primeiro, `quantidade_total` e `filial_id` viviam diretamente em `equipment` (um equipamento = uma filial, uma quantidade).
2. Depois, veio o requisito real: **o mesmo equipamento (mesmo cadastro — nome/categoria/marca/modelo) pode existir em várias filiais ao mesmo tempo, cada uma com sua própria quantidade e seus próprios valores de locação** (o preço pode variar por filial/região). Isso exigiu extrair `quantidade_total`, `valor_diario`, `valor_mensal` e `valor_hora` do `Equipment` para uma tabela filha, `equipment_stock` (um registro por par `(equipamento, filial)`, únicos por essa combinação).

- **`filiais`** continua um cadastro simples (nome, endereço, telefone, observações). Exclusão é bloqueada (`409 Conflict`) se a filial tiver qualquer `equipment_stock` ou `contract_item` vinculado (histórico incluído, não só reservas ativas).
- **`Equipment`** voltou a ser puramente um cadastro de catálogo (nome, categoria, marca, modelo, identificador, localização, observações, fotos, status). Não tem mais `quantidade_total`/`valor_*`/`filial_id` como colunas — `Equipment.quantidade_total` e `Equipment.is_estoque` são **propriedades computadas** a partir da soma de `estoques` (a relação com `EquipmentStock`), não campos persistidos.
- **`EquipmentStock`** (`equipamento_id`, `filial_id`, `quantidade`, `valor_diario`, `valor_mensal`, `valor_hora`) é gerenciado via `PUT/DELETE /equipment/{id}/estoque/{filial_id}` (upsert e remoção; **admin/operador**), separado do CRUD de catálogo do equipamento (`POST/PATCH /equipment`, aberto a qualquer papel). Um equipamento sem nenhum `EquipmentStock` não está disponível em filial nenhuma (`quantidade_total == 0`) e não pode ser reservado em contrato algum.
- **Equipamento serializado vs. item de estoque**: um equipamento com exatamente um `EquipmentStock` de `quantidade == 1` é **serializado** — continua funcionando como antes (status único `disponível/reservado/alugado/manutenção`, controlado pela máquina de estado). Qualquer outra combinação (mais de uma filial, ou quantidade > 1 em qualquer uma) marca `Equipment.is_estoque = True`: o campo `status` deixa de ser significativo — a disponibilidade é calculada dinamicamente por `(equipamento, filial)`.
- **Reserva sempre mira um par `(equipamento, filial)` específico**: `ContractItem.filial_id` é obrigatório — o item de contrato reserva quantidade de UM `EquipmentStock` específico, não do equipamento como um todo. Duas filiais com o mesmo equipamento têm **capacidade totalmente independente**: esgotar o estoque de uma não afeta a disponibilidade da outra.
- **Reserva parcial de estoque**: dentro de um mesmo `(equipamento, filial)`, vários itens de contrato **ativos e simultâneos** (de contratos diferentes) podem coexistir, desde que a soma das quantidades reservadas em qualquer período sobreposto não ultrapasse a `quantidade` daquele `EquipmentStock`.

### Trade-off: perda da `EXCLUDE CONSTRAINT` do Postgres

Antes desta mudança, um equipamento não podia ter dois itens de contrato **ativos** com períodos sobrepostos, e isso era garantido por uma `EXCLUDE CONSTRAINT` no PostgreSQL (`contract_items_no_overlap`, usando `daterange` + `gist`) — era a garantia central que motivou a escolha de Postgres em vez de MongoDB (ver seção 2 do plano). Essa constraint fazia uma checagem binária ("ou o período é exclusivo, ou conflita") que não é mais suficiente quando "conflito" depende de uma soma de quantidades por `(equipamento, filial)` e por período, não de uma simples sobreposição.

A constraint foi **removida** (migration `7a955fcca4cc`, e o modelo final ficou na migration `55274102ae44`). A checagem de conflito agora é feita inteiramente na camada de aplicação (`contract_service.create_contract`/`extend_contract`), assim:

1. `equipment_stock_repository.get_for_update` trava a linha do `EquipmentStock` daquele `(equipamento, filial)` (`SELECT ... FOR UPDATE`) antes de qualquer checagem, serializando requisições concorrentes sobre o mesmo par.
2. `contract_item_repository.sum_quantidade_ativa_overlap` soma a `quantidade` de todos os itens `ATIVO`s desse mesmo `(equipamento, filial)` cujo período se sobrepõe ao solicitado.
3. Se `soma_reservada + quantidade_solicitada > EquipmentStock.quantidade`, a operação falha com `409 Conflict`; senão, o item é criado normalmente.

Isso significa que a garantia de não-overbooking deixou de ser **absoluta a nível de banco** e passou a depender da disciplina da camada de aplicação — mitigado pelo lock de linha, que impede a corrida entre duas requisições concorrentes sobre o mesmo `(equipamento, filial)`, mas não protege contra um `INSERT` direto na tabela fora do fluxo da aplicação. É uma concessão consciente: uma `EXCLUDE CONSTRAINT` simples não consegue expressar "soma ponderada por dois campos não ultrapassa um limite por linha em outra tabela" — isso exigiria uma constraint de agregação que o Postgres não oferece nativamente para esse caso.

Equipamento serializado (`EquipmentStock.quantidade == 1`, uma única filial) continua com a mesma regra de exclusividade de sempre, só que agora aplicada da mesma forma (soma de quantidade, que nesse caso é sempre `1`, não pode ultrapassar `1`) — o comportamento observável para esse caso não muda. Reduzir a `quantidade` de um `EquipmentStock` abaixo do que já está reservado em algum período ativo também é bloqueado (`409`), pelo mesmo motivo.

### Itens de estoque e as transições de contrato

`activate_contract`, `dar_baixa` e `cancel_contract` verificam `equipamento.is_estoque` antes de chamar a máquina de estado do equipamento (`equipment_service.change_status`): para itens de estoque, essa chamada é **pulada inteiramente** — não faz sentido mover um "status único" para um equipamento que pode estar simultaneamente alugado, em filiais diferentes, para vários contratos em quantidades parciais. O status de um item de estoque permanece `disponível` para sempre (nunca é escrito), e a UI trata isso como um indicador informativo, não como fonte de verdade de disponibilidade — a disponibilidade real é sempre calculada por `(equipamento, filial, período)`.

## Decisões sobre pontos que o plano deixava em aberto

O plano (seção 5.4) marcava como "regra a decidir" o que acontece quando uma OS é aberta para um equipamento. Decisão tomada:

- **Abrir uma OS não move o equipamento para `manutenção` automaticamente.** Isso continua sendo uma ação manual e separada via `POST /equipment/{id}/status`. Motivo: nem toda OS aberta justifica tirar o equipamento de operação imediatamente (ex.: uma preventiva agendada para daqui a duas semanas).
- **Concluir ou cancelar uma OS libera o equipamento de volta para `disponível` automaticamente, se ele estava em `manutenção`.** Isso é um requisito explícito do plano (não ambíguo) e foi implementado em `service_order_service._release_equipment_if_in_maintenance`.

O plano (seção 5.3) também marcava como "regra a definir" se a baixa de contrato deveria validar a existência de OS aberta vinculada. **Não implementado** — dar baixa em um contrato não verifica OS abertas. Fica como ponto pendente caso o negócio precise dessa trava no futuro.

## Faturamento (Fase 5)

- Fatura só é gerada automaticamente **se o contrato tiver `valor_total` definido na criação**. Sem `valor_total`, a ativação não gera nenhuma fatura (não há como dividir um valor desconhecido).
- A divisão entre faturas segue `periodicidade_cobranca` do contrato (`unica`, `mensal`, `diaria`), dividindo `valor_total` em partes iguais (o resto de arredondamento fica na última fatura, para a soma bater exatamente com o total). O mesmo critério de divisão é aplicado entre os itens do contrato dentro de cada fatura (`invoice_items`).
- **Baixa de contrato não cancela faturas** — o cliente usou o equipamento, a cobrança segue normalmente. **Cancelamento de contrato cancela** as faturas ainda `pendente`/`atrasada` (faturas já `paga` não são afetadas) — isso segue exatamente a distinção que o plano já fazia na seção 4.2 entre baixa (gera cobrança) e cancelamento (normalmente não gera cobrança).
- **Baixa total exige faturas quitadas**: `dar_baixa` sem `item_ids` (baixa total, que encerra o
  contrato) falha com `409` se houver alguma fatura `pendente`/`atrasada` no contrato
  (`invoice_service.tem_faturas_pendentes`) — força quitar (ou cancelar) antes de encerrar.
  **Baixa parcial não é afetada** — devolver só alguns itens continua liberado mesmo com fatura
  em aberto no contrato. O diálogo de baixa total no frontend (`ContractDetailPage`) lista as
  faturas `pendente`/`atrasada` do contrato com checkbox, soma o valor selecionado e — só para
  `admin`/`financeiro` — permite quitar (registrar pagamento do valor restante de cada uma,
  reaproveitando `POST /invoices/{id}/payments`) direto dali, sem precisar sair da tela do
  contrato; sem essa quitação (ou cancelamento manual da fatura), a baixa total continua
  bloqueada pelo `409` acima.
- Registrar pagamento e cancelar fatura exigem papel `admin` ou `financeiro` — **não** `operador`, que cuida da parte operacional (contratos/equipamentos/OS), não da parte financeira.

## Aditivo de itens em contrato ativo

Cliente com contrato ativo pedindo mais equipamento no meio do prazo (ex.: mais andaimes) não
precisa de um contrato novo — `POST /contracts/{id}/add-items` (`contract_service.add_items`)
adiciona os itens ao contrato existente:

- **Só em contratos `ativo`** — vencido precisa ser estendido primeiro (`InvalidTransitionError`/`409`
  senão), já que não faz sentido um item nascer com período já fora do prazo do contrato.
- **Mesma checagem de estoque** de `create_contract`/`extend_contract`: trava o par
  (equipamento, filial) e confere se cabe no estoque disponível daquela filial no período —
  reaproveita `_checar_disponibilidade`/`equipment_stock_repository.get_for_update`, nenhuma
  lógica nova de disponibilidade.
- **Itens novos herdam o restante do prazo do contrato**: `data_inicio_item = hoje`,
  `data_fim_item = data_fim` do contrato (funciona igual em contrato em aberto, cuja
  `data_fim` é a data-sentinela).
- **Gera um registro em `contract_amendments`** (`tipo = adicao_item`), gravando o período do
  item adicionado em `data_anterior`/`data_nova` (reaproveita as mesmas colunas usadas por
  `extensao`, sem precisar de coluna nova) — assim o histórico de aditivos sempre deixa claro
  de quando a quando o item passou a valer. Os `ContractItem` criados também gravam
  `amendment_id` apontando pra esse registro (não por correlação de datas, que seria ambígua se
  dois aditivos caíssem no mesmo dia), então o histórico consegue listar exatamente quais
  itens cada aditivo adicionou (`ContractAmendment.itens`, exposto em `GET /contracts/{id}/amendments`).
- **O valor do aditivo é sempre calculado automaticamente, nunca digitado pelo admin**, a
  partir do preço já cadastrado no estoque do equipamento (`equipment_stock_repository`),
  conforme a `periodicidade_cobranca` do contrato (`invoice_service.calcular_valor_item_periodo`):
  - `diaria`/`mensal`: `valor_diario`/`valor_mensal` × quantidade × número de dias/meses entre
    hoje e a data final do contrato (mesmo rateio por período de `generate_invoices_for_contract`).
    Sem o preço cadastrado no estoque, a requisição falha com `409` — cadastre o preço antes de
    adicionar.
  - `hora`: não gera fatura na hora — o valor entra na fatura da baixa, junto com o resto do
    contrato (`generate_hourly_invoice` já pega todos os itens ativos, incluindo os adicionados
    depois).
  - `unica`: sem unidade recorrente própria pra ratear — o request precisa informar
    `condicao_cobranca_item` (`"diaria"` ou `"mensal"`) dizendo qual preço do estoque usar pra
    calcular o valor deste item especificamente; `"hora"` não é aceito aqui (`409` — não há
    baixa automática por hora nesse tipo de contrato, então o item nunca seria cobrado). Se
    `condicao_cobranca_item` não for informado, o item é adicionado sem gerar cobrança (fica
    coberto pelo valor fechado já existente do contrato).
  Quando há valor calculado, gera uma fatura avulsa vencendo hoje (ou em
  `data_vencimento_aditivo`, se informado — `invoice_service.generate_addendum_invoice`) e soma
  o valor ao `valor_total` do contrato (só para contrato de prazo fixo — em aberto usa
  `valor_recorrente`, que não faz sentido somar aqui).
- **Exige nova confirmação do cliente via WhatsApp** — adicionar item muda o valor/escopo do
  contrato, então precisa de novo aceite, igual ao fluxo de assinatura do contrato original
  (Fase 3), mas por aditivo: o próprio `ContractAmendment` ganha os mesmos campos
  `assinatura_status`/`assinatura_mensagem_enviada`/`assinatura_enviada_em`/
  `assinatura_resposta_texto`/`assinatura_confirmada_em`/`assinatura_comprovante_key` que
  `Contract` já tinha (populados só quando `tipo = adicao_item`). Ao adicionar o item, se o
  cliente tiver telefone cadastrado, uma mensagem com as mesmas opções fixas "1"/"2" é enviada
  descrevendo o(s) item(ns), o período e o valor; o webhook (`contract_signature_service.
  processar_webhook` → `_encontrar_pendente`) resolve, pelo telefone de quem respondeu, se a
  resposta é para o contrato original ou para um aditivo pendente (o mais recente enviado, caso
  os dois estejam pendentes ao mesmo tempo). Confirmar gera um comprovante em PDF próprio do
  aditivo (`GET /contracts/{id}/amendments/{amendment_id}/comprovante-assinatura`), no mesmo
  padrão do comprovante do contrato original. **Recusar não desfaz nada automaticamente** — nem
  o item, nem a fatura avulsa, nem o `valor_total` já somado — fica só registrado que o cliente
  recusou (mesmo comportamento já existente quando o contrato inteiro é recusado); reverter é
  uma decisão manual de quem administra o contrato.

## Contratos em aberto (sem data final)

Nem todo contrato tem uma data de término conhecida na criação (ex.: locação continuada, sem prazo definido). `POST /contracts` aceita `data_fim: null` para isso.

- **Data-sentinela, não coluna nula de verdade**: internamente, `data_fim`/`contract_items.data_fim_item` continuam `NOT NULL` no banco — um contrato em aberto grava uma data bem distante no futuro (`OPEN_ENDED_SENTINEL_DATE`, 31/12/2099, ver `app/models/contract.py`). A API traduz essa sentinela de volta para `null` na resposta (`ContractRead`/`ContractItemRead`). Essa foi uma escolha deliberada: toda a lógica de reserva de estoque (`sum_quantidade_ativa_overlap`, `_checar_disponibilidade`) já é construída em cima de comparação de intervalos de data reais — tornar essas colunas opcionais exigiria reescrever essa lógica para tratar `NULL` como "infinito" nas duas pontas de cada comparação, sem ganho real (a sentinela já é "infinito" o bastante: nenhuma reserva dura até 2099 de verdade, porque a baixa sempre fecha o item antes disso). O trade-off é que `list_expirable` (contratos vencidos) não precisa de nenhum filtro especial para ignorar contratos em aberto — a sentinela nunca é `< hoje`.
- **Periodicidade `unica` não é permitida em contrato aberto** — cobrança única pressupõe um período fechado para ratear `valor_total`; sem data final, isso não existe. `mensal`, `diária` e `hora` continuam funcionando normalmente.
- **`valor_recorrente` substitui `valor_total`** nesse caso: é o valor cobrado a cada período (não o valor do contrato inteiro, que seria desconhecido). Campo novo, dedicado, para não sobrecarregar o significado de `valor_total` (que continua sendo "valor total do contrato" nos contratos de prazo fixo).
- **Faturamento é gerado aos poucos, não de uma vez**: na ativação, só a fatura do primeiro período é criada (`invoice_service.generate_invoices_for_contract` decide isso olhando `Contract.is_em_aberto`). Um job diário novo, `generate_next_recurring_invoices` (`python -m app.scripts.generate_recurring_invoices`), gera a fatura do próximo período assim que o anterior vence — olhando a fatura mais recente do contrato e comparando com a data de hoje. Se o job ficar um tempo sem rodar, ele gera todos os períodos atrasados de uma vez (não só o próximo), para não deixar buraco na cobrança.
- **Não é possível estender um contrato em aberto** (`POST /contracts/{id}/extend` retorna `409`) — não há data final para empurrar; o contrato já cobra indefinidamente até ser encerrado/cancelado.

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
| Criar/editar/excluir filial | `admin` |
| Listar/ver filial | qualquer papel autenticado |
| Definir/remover estoque de equipamento numa filial (`PUT`/`DELETE /equipment/{id}/estoque/{filial_id}`) | `admin`, `operador` |
| Listar estoque de um equipamento | qualquer papel autenticado |
| Mudar status de equipamento, upload/remoção de foto | `admin`, `operador` |
| Criar/ativar/dar baixa/estender/cancelar contrato | `admin`, `operador` |
| Excluir contrato (só em rascunho) | `admin` |
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

Um **contrato** só pode ser excluído (`DELETE /contracts/{id}`, admin) enquanto estiver em `rascunho` — nunca foi ativado, então não tem fatura, movimentação de estoque nem aditivo associado. Para qualquer outro status, a exclusão falha com `409` e a via correta é cancelar (`POST /contracts/{id}/cancel`), que preserva o histórico.

## Object storage (fotos de equipamento)

Fotos são armazenadas em um bucket S3-compatível (MinIO em desenvolvimento), nunca como binário no banco — `equipment.fotos` guarda só uma lista de chaves. A URL de leitura é gerada sob demanda (presigned URL, expira em 1h), nunca persistida.

## Geração de documento de contrato (PDF)

`GET /contracts/{id}/documento` gera um PDF a partir dos dados do contrato — não existe um endpoint separado para criar/editar o documento, ele é sempre derivado do estado atual do contrato (cliente, itens, período, valor, tipo).

- **`Contract.tipo`** (`locacao` | `servico`, default `locacao`) é escolhido na **criação** do contrato e persistido — não é mais uma escolha feita no momento do download. Determina o modelo de cláusulas usado ao gerar o PDF ("Contrato de Locação de Equipamentos" com LOCADORA/LOCATÁRIA, ou "Contrato de Prestação de Serviços" com PRESTADORA/CONTRATANTE — serviço realizado com operação do equipamento) e aparece como selo na lista/detalhe do contrato na interface. `GET /contracts/{id}/documento` não recebe mais parâmetro de tipo — ele lê `contract.tipo` diretamente.
- **Dados do locador/prestador** (razão social, CNPJ, endereço) vêm de configuração fixa da aplicação (`settings.company_name`/`company_document`/`company_address`, variáveis de ambiente `COMPANY_*`), não de um cadastro no banco — a empresa que opera o sistema é sempre a mesma "parte fixa" em todo contrato gerado.
- **Valor de referência por item**: se o item já tem `valor_item` calculado (contrato com baixa registrada ou fatura gerada), esse valor aparece no documento. Caso contrário, tenta usar o valor do `EquipmentStock` daquele `(equipamento, filial)` correspondente à `periodicidade_cobranca` do contrato (`valor_diario`/`valor_mensal`/`valor_hora`); para periodicidade `unica`, não há valor de referência por item — só o `valor_total` do contrato aparece na cláusula de valor.
- **Cláusula de multa por atraso**: o documento inclui uma cláusula "Da mora e multa por atraso" citando o mesmo `late_fee_percentage` (`app/config/settings.py`) usado pelo job `mark_overdue_invoices` — o texto do contrato e a multa efetivamente aplicada nas faturas usam a mesma fonte de verdade, nunca podem divergir.
- **Aviso legal explícito**: o modelo de cláusulas é genérico (partes, objeto, prazo, valor, obrigações, responsabilidade por danos, rescisão, mora, foro) e o próprio PDF inclui um aviso de que não constitui aconselhamento jurídico e deve ser revisado por advogado antes de uso formal — decisão explícita do usuário ao pedir a feature, não uma limitação escondida.
- Implementado com `xhtml2pdf` (HTML/CSS → PDF, puramente Python — sem dependências nativas como Cairo/Pango, o que simplifica a imagem Docker) e templates Jinja2 em `app/templates/` (`contract_base.html` com as seções comuns — partes, mora, foro, assinaturas, aviso legal — e `contract_locacao.html`/`contract_servico.html` estendendo-o com as cláusulas específicas de cada variante).

## Integração com WhatsApp (Evolution API) — Fase 1: envio de cobrança e contrato

`POST /invoices/{id}/send-whatsapp` e `POST /contracts/{id}/send-whatsapp` enviam mensagens
via [Evolution API](https://github.com/EvolutionAPI/evolution-api) (serviço Docker próprio,
`docker-compose.yml`, service `evolution-api`) — não usamos `whatsapp-web.js` (rodaria um
processo Node+Puppeteer embutido, mais frágil e pesado) nem a API oficial do WhatsApp Business
(exige aprovação de conta comercial da Meta; Evolution API é mais rápido de colocar no ar para
o volume desse sistema).

- **Só envio (outbound)** nesta fase — não há webhook de recebimento nem confirmação
  automática de leitura/resposta do cliente.
- **Telefone do cliente**: usa `Client.telefone` (campo já existente, formato livre) —
  `app/config/whatsapp.py::normalize_phone_br` remove tudo que não é dígito e garante o DDI
  55 na frente. Se o cliente não tiver telefone cadastrado, ambos os endpoints retornam `409`.
- **Cobrança de fatura** (`invoice_service.send_invoice_whatsapp`): mensagem de texto simples
  citando valor, vencimento e, se a fatura estiver `atrasada`, a multa já aplicada
  (`invoice.multa_juros_aplicado`) — mesma fonte de verdade do job `mark_overdue_invoices`.
- **Envio de contrato para assinatura** (`contract_document_service.send_contract_whatsapp`):
  gera o mesmo PDF de `GET /contracts/{id}/documento` (reaproveita `generate_contract_pdf`),
  envia como documento anexado (base64) com uma legenda pedindo a assinatura.
- **Erros da Evolution API** (rede fora do ar, instância desconectada, etc.) viram
  `ExternalServiceError` → HTTP `502` — distinto do `409` de validação de dados, para o
  frontend conseguir diferenciar "não configurado corretamente" (nosso lado) de "cliente sem
  telefone" (dado faltando).
- **Configuração** via `EVOLUTION_API_URL`/`EVOLUTION_API_KEY`/`EVOLUTION_INSTANCE_NAME`
  (`.env`) — o pareamento do número de WhatsApp (escanear o QR code) agora pode ser feito pela
  tela de Configurações (ver seção "Fase 2" abaixo) ou por `curl` (ver README).
- **Payload confirmado contra uma instância real** da Evolution API v2.3.0 durante o
  desenvolvimento (`message/sendText`, `message/sendMedia`, `instance/create`,
  `instance/connectionState`, `instance/connect`, `instance/logout`) — não é só documentação
  lida, foi testado ao vivo. Ainda assim, versões futuras da Evolution API podem mudar o
  contrato da API.
- **Imagem Docker correta é `evoapicloud/evolution-api`, não `atendai/evolution-api`** — o
  projeto migrou de organização no Docker Hub a partir da v2.3.0; `atendai/evolution-api` não
  existe mais (retorna "repository does not exist" mesmo sendo um erro de pull genérico do
  Docker, não um problema de rede/autenticação).
- **Fase 3 (implementada, ver seção própria abaixo)**: confirmação de aceite do contrato via
  resposta do cliente no WhatsApp, com comprovante gerado automaticamente.

## Integração com WhatsApp — Fase 2: templates de mensagem e conexão pela interface

- **`MessageTemplate`** (`app/models/message_template.py`): tabela com uma linha por `chave`
  (`cobranca_fatura` | `contrato_assinatura`), `conteudo` (o texto, com variáveis `{nome}`) e
  `updated_at`. Seedada com o texto default na própria migration
  (`af37bd32585c_adiciona_tabela_message_templates.py`) — o mesmo texto que antes estava
  hardcoded em `invoice_service.py`/`contract_document_service.py`.
- **`message_template_service.render(db, chave, **kwargs)`** busca a linha e aplica
  `.format(**kwargs)`; se a linha não existir (não deveria acontecer em uso normal, já que a
  migration sempre seeda as duas), cai no texto default hardcoded em
  `DEFAULT_TEMPLATES` como rede de segurança.
- **Validação na escrita** (`PUT /settings/message-templates/{chave}`): antes de salvar, o
  `conteudo` é testado com `.format()` usando só as variáveis válidas daquela `chave`
  (`PLACEHOLDERS` em `message_template_service.py`) — usar uma variável não reconhecida (ex.
  `{campo_errado}`) ou formatação quebrada (`{` sem fechar) falha com `409` **na hora de
  salvar**, não só quando uma cobrança real tentasse usar o template quebrado.
- **Conexão WhatsApp pela interface**: `GET /settings/whatsapp/status` reflete o estado real
  da instância na Evolution API (não guarda estado próprio no banco); `POST
  /settings/whatsapp/connect` cria a instância na primeira vez (`instance/create`, que já
  retorna o QR code) ou busca um QR novo se a instância já existe mas não está `open`
  (`instance/connect`) — os dois endpoints têm formatos de resposta diferentes na Evolution
  API (`instance/create` aninha em `qrcode.base64`, `instance/connect` retorna `base64` direto
  na raiz), normalizados em `whatsapp_connection_service.py` para o frontend sempre receber o
  mesmo formato `{estado, qrcode_base64}`.
- Todas as rotas de `/settings` são **admin only** — tanto ver quanto editar templates, tanto
  ver status quanto conectar/desconectar o WhatsApp.

## Integração com WhatsApp — Fase 3: confirmação de aceite do contrato

Justiça brasileira já aceita conversa de WhatsApp como prova, e locação de equipamento não
exige forma solene (**art. 107 do Código Civil** — liberdade de forma). Em vez de só entregar
o PDF do contrato, o sistema agora pede uma confirmação explícita do cliente e gera um
comprovante formatado a partir dessa troca — não um screenshot real (nenhuma API de WhatsApp
oferece isso), mas um documento profissional com o mesmo padrão visual do contrato em PDF.

- **`Contract.assinatura_status`** (`nao_enviado` | `aguardando_confirmacao` | `confirmado` |
  `recusado`, em `app/models/contract.py`) junto com `assinatura_mensagem_enviada`,
  `assinatura_enviada_em`, `assinatura_resposta_texto`, `assinatura_confirmada_em` (nome
  mantido por compatibilidade — na prática é "respondida_em", preenchido tanto na confirmação
  quanto na recusa), `assinatura_comprovante_key`. Sem histórico de múltiplos reenvios —
  reenviar o contrato (`POST /contracts/{id}/send-whatsapp`) sobrescreve o estado anterior e
  volta pra `aguardando_confirmacao`.
- **Opções numeradas, não uma palavra-chave**: a primeira versão pedia `"responda com: CONFIRMAR {id}"`,
  mas isso é ruim para o cliente final (confuso, fácil de digitar errado). A mensagem agora
  termina com:
  ```
  Para continuar, responda com o número da opção:
  1 - Aceito os termos e condições
  2 - Não aceito os termos
  ```
  Essas opções são fixas, **não vêm do template editável** (só a legenda antes delas vem do
  template `contrato_assinatura`) — fixas de propósito, porque o webhook só reconhece a
  resposta `"1"` ou `"2"` (comparação exata, após `strip()`); deixar editável quebraria a
  detecção se um admin mudasse o texto sem saber disso.
- **Sem número de contrato na resposta ⇒ busca por telefone**: como o cliente só manda "1" ou
  "2" (sem o número do contrato), o webhook não pode mais extrair o `contract_id` da mensagem
  — em vez disso, `contract_repository.list_aguardando_confirmacao` lista todos os contratos
  `aguardando_confirmacao` e `_encontrar_contrato_aguardando` acha, entre eles, o que pertence
  a um cliente cujo `telefone` (normalizado) bate com quem respondeu; se mais de um bater
  (dois clientes com o mesmo telefone, ou o mesmo cliente com dois contratos pendentes — não
  deveria ser comum), fica com o mais recente por `assinatura_enviada_em`. Escanear todos os
  `aguardando_confirmacao` é aceitável porque essa lista tende a ser pequena a qualquer momento.
- **Webhook** (`POST /webhooks/whatsapp/{secret}`, `app/services/contract_signature_service.py::processar_webhook`):
  configurado automaticamente na Evolution API sempre que `POST /settings/whatsapp/connect` é
  chamado (`whatsapp_connection_service._configurar_webhook`), apontando pro hostname interno
  do Docker (`http://backend:8000`, mesmo padrão do MinIO) — não precisa expor a porta do
  backend pra internet. Ignora mensagens enviadas por nós mesmos (`fromMe`) e qualquer texto
  que não seja exatamente `"1"` ou `"2"`. Qualquer coisa que não bater é ignorada
  silenciosamente, sempre `200`.
- **Bug real encontrado e corrigido ao vivo (duas rodadas)**: `data.key.remoteJid` às vezes
  vem no formato `"119005423624412@lid"` ("linked ID", um identificador que o WhatsApp usa em
  vez do número de telefone em determinadas situações) em vez de
  `"5511999999999@s.whatsapp.net"` — extrair o telefone só de `remoteJid` fazia a confirmação
  nunca bater. O número de telefone real, nesse caso, vem em `senderPn` — **mas dentro de
  `data.key.senderPn`, não em `data.senderPn`** (a primeira correção olhou o campo certo no
  lugar errado do payload; o teste automatizado escrito na hora também modelou o payload de
  teste errado, então passou mesmo com o bug de produção presente — só apareceu numa resposta
  real do usuário). `_extrair_telefone` (`contract_signature_service.py`) agora lê
  `key.get("senderPn")` corretamente, com fallback pra `key.get("remoteJid")`. Lição: quando o
  formato de um payload de webhook externo vem só de documentação/memória, testar contra uma
  resposta real (não só um payload de teste que você mesmo escreveu) é o que realmente prova
  que o parsing está certo.
- **Resposta "1" (aceito)** → `contract_signature_service.confirmar`: marca `confirmado`,
  gera o Comprovante de Aceite Eletrônico (ver abaixo) e **envia de volta pelo WhatsApp** uma
  mensagem de agradecimento usando o template editável `aceite_confirmado`, com o prazo de
  entrega = `Contract.data_inicio` formatada (reaproveita o campo que já existe — é a data que
  o aluguel/serviço começa, ou seja, quando o equipamento precisa ser entregue; nenhum campo
  novo foi criado para isso).
- **Resposta "2" (não aceito)** → `contract_signature_service.recusar`: marca `recusado`,
  **não** gera comprovante (não haveria o que provar), e envia de volta uma mensagem de
  reconhecimento usando o template editável `aceite_recusado`.
- **Comprovante de Aceite Eletrônico** (`contract_signature_service.generate_comprovante_pdf`,
  template `app/templates/comprovante_aceite.html`): PDF com a mensagem enviada e a resposta
  do cliente, cada uma com seu timestamp, mais uma declaração formal citando o art. 107 do CC
  — mesmo aviso legal genérico já usado no contrato (revisar com jurídico antes de uso formal,
  principalmente em contratos de maior valor/risco, onde uma assinatura eletrônica
  certificada — ICP-Brasil ou plataforma como Clicksign/ZapSign/Autentique — é mais robusta
  que este fluxo). Armazenado no MinIO (`storage.upload_file`/`download_file`, mesmo bucket
  das fotos de equipamento) e servido via `GET /contracts/{id}/comprovante-assinatura` (`404`
  se o contrato não estiver `confirmado`).
- **Fora do escopo desta fase (pedido futuro do usuário)**: agendamento de entrega com
  data/horário/local específicos e um mapa/rota no frontend (provavelmente OpenStreetMap +
  Leaflet, sem chave de API, com um link "Abrir rota no Google Maps" para navegação de
  verdade) — por ora, o "prazo de entrega" informado é só a `data_inicio` já existente do
  contrato.

## Preparado para a API oficial do WhatsApp (Cloud API), via a própria Evolution API

Não existe (nem precisa existir) um segundo cliente HTTP para falar direto com a Meta — a
própria Evolution API já sabe conversar tanto com o WhatsApp não-oficial (Baileys, QR code)
quanto com a API oficial (Cloud API da Meta, modo `"WHATSAPP-BUSINESS"`) por baixo dos panos,
dependendo de como a instância foi criada. `send_text`, `send_document`,
`get_connection_state`, `fetch_qrcode` e `logout_instance` em `app/config/whatsapp.py` **não
mudam em nada** entre os dois modos — só o corpo de `POST /instance/create` muda
(`create_instance()`):

- **Modo padrão (hoje, sem nada configurado)**: `{"instanceName": ..., "qrcode": true, "integration": "WHATSAPP-BAILEYS"}` — QR code, como já está em uso.
- **Modo API oficial**: quando `META_WHATSAPP_TOKEN` e `META_WHATSAPP_NUMBER_ID` (mais
  `META_WHATSAPP_BUSINESS_ID`) estão preenchidos no `.env`, `create_instance()` monta
  `{"instanceName": ..., "qrcode": false, "integration": "WHATSAPP-BUSINESS", "token": ..., "number": ..., "businessId": ...}`
  em vez disso — sem QR code, autenticado com o token permanente do Meta Business Manager.
- Ativar a API oficial no futuro é só preencher essas três variáveis no `.env` e clicar em
  "Conectar" de novo na tela de Configurações — nenhum código muda, nenhum outro arquivo do
  backend ou frontend precisa ser tocado. Testado (`test_whatsapp_business_integration.py`)
  que o corpo da requisição muda corretamente conforme a configuração; o fluxo completo contra
  uma conta real da Meta não pôde ser testado ao vivo (não há credenciais disponíveis agora).
