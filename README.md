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

Para aplicar as migrations do banco (dentro do container do backend):

```bash
docker compose exec backend alembic upgrade head
```

### Scripts administrativos

Rodar dentro do container do backend (`docker compose exec backend <comando>`) ou localmente com o venv ativado:

```bash
# Cria o usuário admin inicial (idempotente — não faz nada se o email já existir)
ADMIN_EMAIL=admin@exemplo.com ADMIN_PASSWORD=senha-forte python -m app.scripts.seed_admin

# Job diário: marca como "vencido" todo contrato ativo cuja data_fim já passou
python -m app.scripts.mark_expired_contracts
```

O `mark_expired_contracts` precisa rodar periodicamente (uma vez por dia é suficiente) para manter o status dos contratos em dia — ele não roda sozinho. Agende via cron (Linux/no host) ou Agendador de Tarefas do Windows, por exemplo:

```bash
# crontab -e — todo dia às 00:05
5 0 * * * docker compose -f /caminho/docker-compose.yml exec -T backend python -m app.scripts.mark_expired_contracts
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

Rodar os testes:

```bash
pytest app/tests
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
