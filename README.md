# Lanstar — Enterprise Template

Template corporativo de autenticação e autorização (RBAC) com Clean Architecture,
DDD, CQRS, Vertical Slice, Command Bus, Event Bus e Dependency Injection.

## Stack

| Camada | Tecnologias |
|--------|-------------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, Redis, JWT |
| Frontend | Vue 3, Pinia, Vue Router, Axios, Quasar |

## Etapas

| # | Conteúdo | Status |
|---|----------|--------|
| 1 | Fundação: Shared Kernel, Buses, UoW, DI, bootstrap | Concluída |
| 2 | Módulo Permissions + Roles | Concluída |
| 3 | Módulo Users + associações | Concluída |
| 4 | Authentication (JWT + Refresh) | Concluída |
| 5 | Autorização RBAC + Rate Limiting | Concluída |
| 6 | Dashboard API | Concluída |
| 7 | Frontend Vue/Quasar + permissões | Concluída |
| 8 | Seed (roles ADMIN…VIEWER + usuário demo) | Concluída |
| 9 | Docker Compose completo (API + frontend) | Concluída |

## Pré-requisitos

- Python 3.13+
- Docker / Docker Compose
- Node.js 20+

## Stack completa (Docker)

```bash
docker compose up -d --build
docker compose --profile seed run --rm seed
```

- App: http://134.209.122.250:9000 (também http://localhost:9000)
- API: http://134.209.122.250:8000 (também http://localhost:8000)
- Login demo: `galileu@lanstar.com.br` / `Demo@12345`

## Infraestrutura apenas (Postgres + Redis)

```bash
docker compose up -d postgres redis
```

## Backend (desenvolvimento local)

```bash
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head
python -m scripts.seed
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend (desenvolvimento local)

```bash
cd frontend
npm install
npm run dev
```

App: http://134.209.122.250:9000 (proxy `/api` → backend `:8000`)

## Seed

O seed é idempotente e cria:

- todas as permissões canônicas
- roles `ADMIN`, `MANAGER`, `OPERATOR`, `CLIENT`, `VIEWER`
- usuário `galileu@lanstar.com.br` / `Demo@12345` com role `ADMIN`

O **ADMIN** (Galileu) tem apenas:

- CRUD de usuários, roles e permissões
- `dashboard.admin` (painel de administração RBAC)

Não recebe: `dashboard.manager|operator|client|viewer` nem `system.settings`.

```bash
cd backend
python -m scripts.seed
```

## Testes

```bash
cd backend
pytest -v
```

## Arquitetura (resumo)

```
Cliente → FastAPI (Gateway)
       → AuthN / AuthZ / Validation / Rate Limit
       → CommandBus / QueryBus
       → Handler
       → Domain (Aggregates, VOs, Events)
       → Repository + UnitOfWork
       → PostgreSQL
       → EventBus (pós-commit) → Audit / Logs / Notifications
```

Módulos em `src/modules/*` são Vertical Slices independentes.
Comunicação entre módulos: Commands, Queries, Domain Events e Interfaces — nunca imports internos.

Para adicionar páginas, módulos, widgets ou ações protegidas pelo RBAC, siga o playbook em [HOWTODO.md](HOWTODO.md).
