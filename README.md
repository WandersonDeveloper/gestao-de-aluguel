# Gestão de Aluguéis de Equipamentos

Sistema de gestão de aluguel de equipamentos (cadastros, disponibilidade, contratos, ordens de serviço e financeiro).

- Plano completo: [docs/plano-sistema-alugueis.md](docs/plano-sistema-alugueis.md)
- Referência da API: [docs/api.md](docs/api.md) (ou `/docs` com o backend rodando)
- Regras de negócio e decisões de implementação: [docs/regras-de-negocio.md](docs/regras-de-negocio.md)

## Stack

- **Backend:** Python + FastAPI + SQLAlchemy + Alembic
- **Frontend:** React + TypeScript (Vite)
- **Banco de dados:** PostgreSQL
- **Object storage:** MinIO (compatível com S3) — fotos de equipamento

## Pré-requisitos

- Docker Desktop (recomendado para rodar tudo de uma vez)
- Ou, para rodar sem Docker: Python 3.12+ e Node 20+

## Rodando com Docker Compose (recomendado)

```bash
docker compose up --build
```

- Backend: http://localhost:8000 (docs automáticos em `/docs`)
- Frontend: http://localhost:5173
- PostgreSQL: `localhost:5432` (usuário/senha/banco: `alugueis`)
- MinIO: console em http://localhost:9001 (usuário `alugueis` / senha `alugueis123`), API S3 em `localhost:9000`
- Evolution API (integração WhatsApp): http://localhost:8080 — ver configuração abaixo

Para aplicar as migrations do banco (dentro do container do backend):

```bash
docker compose exec backend alembic upgrade head
```

### Configurando a integração com WhatsApp (Evolution API)

O envio de cobrança de fatura e de contrato para assinatura via WhatsApp (ver
`docs/regras-de-negocio.md`) usa a [Evolution API](https://github.com/EvolutionAPI/evolution-api)
(imagem `evoapicloud/evolution-api` — o projeto migrou de `atendai/evolution-api` a partir da
v2.3.0), que já sobe junto no `docker compose up`. Falta um passo manual único, feito uma vez,
para parear seu número de WhatsApp — o jeito mais fácil é pela própria interface:

1. Faça login como **admin** e abra **Configurações** no menu lateral.
2. Clique em "Conectar" na seção "Conexão WhatsApp" — a tela mostra um QR code.
3. No celular, abra WhatsApp > Aparelhos conectados > Conectar um aparelho, e escaneie.
4. O status muda para "Conectado" automaticamente assim que o pareamento é concluído.

Ainda é possível fazer isso por `curl`, direto na Evolution API, se preferir (útil para
depuração):

```bash
# Criar a instância (troque "change-me" pela mesma EVOLUTION_API_KEY do backend/.env;
# o banco "evolution" é criado automaticamente pela própria Evolution API na subida)
curl -X POST http://localhost:8080/instance/create \
  -H "apikey: change-me" -H "Content-Type: application/json" \
  -d '{"instanceName": "gestao-alugueis", "qrcode": true, "integration": "WHATSAPP-BAILEYS"}'

# Pegar um QR code novo, se precisar reparear (abra a imagem em "base64" e escaneie)
curl http://localhost:8080/instance/connect/gestao-alugueis -H "apikey: change-me"
```

Depois de parear, os botões "Enviar cobrança via WhatsApp" (fatura) e "Enviar contrato para
assinatura via WhatsApp" (contrato) na interface já funcionam. Sem isso configurado, esses
botões retornam erro 502. O texto dessas mensagens também pode ser personalizado na tela de
Configurações, seção "Templates de mensagem".

O passo "Conectar" também configura sozinho, na Evolution API, o webhook usado para detectar
quando o cliente confirma que aceita os termos do contrato (respondendo `CONFIRMAR {número do
contrato}` no WhatsApp) — nenhum passo manual adicional é necessário. Ver `docs/regras-de-negocio.md`
para os detalhes desse fluxo e do comprovante de aceite gerado automaticamente.

### Scripts administrativos

Rodar dentro do container do backend (`docker compose exec backend <comando>`) ou localmente com o venv ativado:

```bash
# Cria o usuário admin inicial (idempotente — não faz nada se o email já existir)
ADMIN_EMAIL=admin@exemplo.com ADMIN_PASSWORD=senha-forte python -m app.scripts.seed_admin

# Job diário: marca como "vencido" todo contrato ativo cuja data_fim já passou
python -m app.scripts.mark_expired_contracts

# Job diário: marca fatura pendente vencida como "atrasada" e aplica a multa configurada
python -m app.scripts.mark_overdue_invoices

# Job diário: gera a próxima fatura de contratos "em aberto" (sem data final) com
# valor_recorrente definido, assim que o período anterior vence
python -m app.scripts.generate_recurring_invoices

# Dados de demonstração para testar a interface (clientes, equipamentos, contratos em
# vários estágios, faturas, OS). Seguro rodar mais de uma vez — pula o que já existe.
python -m app.scripts.seed_demo_data
```

Esses três jobs diários não rodam sozinhos — agende via cron (Linux/no host) ou Agendador de Tarefas do Windows, por exemplo:

```bash
# crontab -e — todo dia às 00:05
5 0 * * * docker compose -f /caminho/docker-compose.yml exec -T backend python -m app.scripts.mark_expired_contracts
6 0 * * * docker compose -f /caminho/docker-compose.yml exec -T backend python -m app.scripts.mark_overdue_invoices
7 0 * * * docker compose -f /caminho/docker-compose.yml exec -T backend python -m app.scripts.generate_recurring_invoices
```

## Rodando sem Docker

### Backend

```bash
cd backend
python -m venv venv
./venv/Scripts/activate   # Windows
pip install -r requirements-dev.txt
cp .env.example .env      # ajuste DATABASE_URL para seu Postgres local
alembic upgrade head
uvicorn app.main:app --reload
```

### Testes

**Importante:** os testes devem rodar contra um banco **separado** do banco de desenvolvimento
(`alugueis_test`, não `alugueis`) — o banco de dev normalmente tem dados de demonstração
(`seed_demo_data.py`) que colidem com valores fixos usados em alguns testes (documento,
nome de categoria, etc.), causando falhas por conflito de unicidade que não têm nada a
ver com o código.

```bash
# uma vez, para criar o banco de testes:
docker compose exec db psql -U alugueis -d alugueis -c "CREATE DATABASE alugueis_test OWNER alugueis;"
DATABASE_URL=postgresql+psycopg2://alugueis:alugueis@localhost:5432/alugueis_test alembic upgrade head

# a cada execução dos testes:
DATABASE_URL=postgresql+psycopg2://alugueis:alugueis@localhost:5432/alugueis_test pytest app/tests
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Estrutura do projeto

```
backend/
  app/
    controllers/   # handlers dos endpoints
    routes/        # APIRouters, agregação de rotas
    services/      # regras de negócio e orquestração
    domain/        # máquinas de estado (equipamento, contrato, OS, fatura)
    repositories/   # acesso a dados
    models/         # modelos SQLAlchemy
    schemas/        # schemas Pydantic
    config/         # settings e conexão com banco
    tests/          # testes unitários e de integração
  alembic/          # migrations do banco

frontend/
  src/
    components/
    pages/
    routes/
    services/
    hooks/
    context/
    styles/

docs/
  plano-sistema-alugueis.md
```
