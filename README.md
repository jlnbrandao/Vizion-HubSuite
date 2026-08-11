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
| 11 | Hardening multi-tenant + platform provisioning | Concluída |

## Pré-requisitos

- Python 3.13+
- Docker / Docker Compose
- Node.js 20+

## Multi-tenancy (RLS)

- Tabela `tenants`; seed cria **`bigbang`** (app) e **`platform`** (ops).
- `users`, `roles`, `permissions`, `user_roles` e `role_permissions` são isolados por `tenant_id` com **FORCE ROW LEVEL SECURITY**.
- `tenants` SELECT é restrito ao tenant atual (ou `rls_bypass`); resolução por Host usa a função **`resolve_tenant_by_slug`** (`SECURITY DEFINER`).
- O slug do tenant vem do **subdomínio do Host** (primeiro label):
  - `bigbang.lanstar.com.br`
  - `bigbang.<ip>`
  - `bigbang.localhost` (desenvolvimento)
- Hosts são validados contra `ALLOWED_TENANT_BASE_DOMAINS` (default: `localhost,lanstar.com.br`).
- Login **não** tem campo de tenant: acesse a app pelo host do tenant.
- JWT e refresh session carregam `tenant_id` / `tenant_slug`; token de um tenant é rejeitado se o Host for de outro.
- Repositórios SQLAlchemy também filtram por `tenant_id` (defense-in-depth além do RLS).
- Cada request autenticada **revalida** no banco `is_active`, `tenant_id` e `role_ids` do usuário.

### Roles de banco (least-privilege)

| Role | Uso |
|------|-----|
| `lanstar` | Owner / Alembic (`DATABASE_MIGRATE_URL`) |
| `lanstar_app` | API em runtime (`DATABASE_URL`) — sujeito a FORCE RLS |
| `lanstar_migrate` | Opcional, com `BYPASSRLS` para jobs privilegiados |

Rotacione as senhas padrão (`lanstar_app` / `lanstar_migrate`) em produção.

### Platform admin

- Permissões `tenants.*` + `system.settings` existem só no tenant **`platform`** (não no RBAC comum).
- API: `GET/POST /api/v1/tenants`, rename, activate/deactivate — exige permissões `tenants.*`.
- Login: http://platform.localhost:9000 — usuário `platform` / `123Mudar.`

## Autenticação e autorização

| Peça | Comportamento |
|------|----------------|
| Access token | JWT HS256 (~15 min), enviado no header `Authorization: Bearer` |
| Refresh token | Opaco, Redis TTL 7 dias, cookie **httpOnly** (`lanstar_refresh_token`, `SameSite=lax`, `Secure` fora de development) |
| Frontend | Access só em **memória** (não persiste em `localStorage`); bootstrap/refresh usam o cookie |
| AuthZ | `Depends(require_permission(...))` no backend; UI espelha com `can()` / `meta.permissions` |
| Hierarquia | Roles ranqueadas (`PLATFORM` > `ADMIN` > `MANAGER` > …): quem tem `users.update` **não** gerencia pares ou superiores |
| Sessões | Refresh recarrega `role_ids` / `is_active` do banco; senha, desativação, delete ou troca de roles invalida todos os refresh tokens do usuário |
| Rate limit | Chave `tenant:IP` (respeita `X-Forwarded-For` / `X-Real-IP`) |

Em produção (`APP_ENV` ≠ `development`):

- `JWT_SECRET_KEY` ≥ 32 caracteres (placeholders rejeitados)
- `ALLOWED_TENANT_BASE_DOMAINS` obrigatório

## Stack completa (Docker)

```bash
docker compose up -d --build
docker compose --profile seed run --rm seed
```

- App (tenant bigbang): http://bigbang.localhost:9000  
  (ou `http://bigbang.<servidor>:9000` / DNS `bigbang.lanstar.com.br`)
- Platform: http://platform.localhost:9000
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
alembic upgrade head   # usa DATABASE_MIGRATE_URL
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

### Tenant `bigbang`

- permissões de produto (sem `tenants.*` / `system.settings`)
- roles `ADMIN`, `MANAGER`, `OPERATOR`, `CLIENT`, `VIEWER`
- usuários demo (senha `123Mudar.`):

| username | email | role |
|---|---|---|
| `galileu` | `galileu@lanstar.com.br` | `ADMIN` |
| `manager` | `manager@lanstar.com.br` | `MANAGER` |
| `operator` | `operator@lanstar.com.br` | `OPERATOR` |
| `user` | `user@lanstar.com.br` | `CLIENT` |
| `viewer` | `viewer@lanstar.com.br` | `VIEWER` |

O **ADMIN** (Galileu) tem apenas CRUD de usuários/roles/permissões e `dashboard.admin`.

### Tenant `platform`

| username | email | role |
|---|---|---|
| `platform` | `platform@lanstar.com.br` | `PLATFORM` |

Permissões: `tenants.create|read|update|activate|deactivate` e `system.settings`.

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
Cliente (bigbang.* | platform.*) → FastAPI Gateway
       → TenantMiddleware (Host allowlist → resolve_tenant_by_slug → RLS GUC)
       → RateLimit (tenant:IP)
       → AuthN (JWT + reload user) / AuthZ / Validation
       → CommandBus / QueryBus
       → Handler
       → Domain (Aggregates, VOs, Events)
       → Repository (filtro tenant_id) + UnitOfWork (SET LOCAL app.current_tenant_id)
       → PostgreSQL FORCE RLS
       → EventBus (pós-commit) → Audit / Logs / Notifications
```

Módulos em `src/modules/*` são Vertical Slices independentes.
Comunicação entre módulos: Commands, Queries, Domain Events e Interfaces — nunca imports internos.

Para adicionar páginas, módulos, widgets ou ações protegidas pelo RBAC, siga o playbook em [HOWTODO.md](HOWTODO.md).
