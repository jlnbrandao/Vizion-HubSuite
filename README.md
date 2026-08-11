# Lanstar — Enterprise Template

Template corporativo de autenticação e autorização (RBAC) com multi-tenancy
(PostgreSQL RLS), Clean Architecture, DDD, CQRS, Vertical Slice, Command Bus,
Event Bus e Dependency Injection.

## Stack

| Camada | Tecnologias |
|--------|-------------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (RLS), Redis, JWT |
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
| 10 | Multi-tenant + Postgres RLS (subdomínio) | Concluída |

## Pré-requisitos

- Python 3.13+
- Docker / Docker Compose
- Node.js 20+

## Multi-tenancy (RLS)

- Tabela `tenants`; seed cria o tenant **`bigbang`**.
- `users`, `roles`, `permissions`, `user_roles` e `role_permissions` são isolados por `tenant_id` com **FORCE ROW LEVEL SECURITY**.
- O slug do tenant vem do **subdomínio do Host** (primeiro label):
  - `bigbang.lanstar.com.br`
  - `bigbang.<ip>`
  - `bigbang.localhost` (desenvolvimento)
- Login **não** tem campo de tenant: acesse a app pelo host do tenant.
- JWT e refresh session carregam `tenant_id` / `tenant_slug`; token de um tenant é rejeitado se o Host for de outro.

## Stack completa (Docker)

```bash
docker compose up -d --build
docker compose --profile seed run --rm seed
```

- App (tenant bigbang): http://bigbang.localhost:9000  
  (ou `http://bigbang.<servidor>:9000` / DNS `bigbang.lanstar.com.br`)
- API: mesma origem via proxy `/api` (Host preservado)
- Login demo: `galileu` ou `galileu@lanstar.com.br` / `123Mudar.`

Não use `http://localhost:9000` sem subdomínio — a API exige slug no Host.

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

Chamadas locais à API devem enviar `Host: bigbang.localhost` (ex.: curl `-H 'Host: bigbang.localhost'`).

## Frontend (desenvolvimento local)

```bash
cd frontend
npm install
npm run dev
```

Abra **http://bigbang.localhost:9000** (proxy `/api` → backend `:8000` com `changeOrigin: false` para preservar o Host).

## Seed

O seed é idempotente e cria:

- tenant `bigbang` (nome Bigbang)
- todas as permissões canônicas **no tenant**
- roles `ADMIN`, `MANAGER`, `OPERATOR`, `CLIENT`, `VIEWER` **no tenant**
- usuários demo no tenant (senha `123Mudar.`):

| username | email | role |
|---|---|---|
| `galileu` | `galileu@lanstar.com.br` | `ADMIN` |
| `manager` | `manager@lanstar.com.br` | `MANAGER` |
| `operator` | `operator@lanstar.com.br` | `OPERATOR` |
| `user` | `user@lanstar.com.br` | `CLIENT` |
| `viewer` | `viewer@lanstar.com.br` | `VIEWER` |

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
Cliente (bigbang.*) → FastAPI Gateway
       → TenantMiddleware (Host → tenant + RLS GUC)
       → AuthN / AuthZ / Validation / Rate Limit
       → CommandBus / QueryBus
       → Handler
       → Domain (Aggregates, VOs, Events)
       → Repository + UnitOfWork (SET LOCAL app.current_tenant_id)
       → PostgreSQL RLS
       → EventBus (pós-commit) → Audit / Logs / Notifications
```

Módulos em `src/modules/*` são Vertical Slices independentes.
Comunicação entre módulos: Commands, Queries, Domain Events e Interfaces — nunca imports internos.

Para adicionar páginas, módulos, widgets ou ações protegidas pelo RBAC, siga o playbook em [HOWTODO.md](HOWTODO.md).
