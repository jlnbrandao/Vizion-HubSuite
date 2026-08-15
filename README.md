# Lanstar — Enterprise Template

Template corporativo de autenticação e autorização (RBAC) com multi-tenancy
(PostgreSQL RLS), Clean Architecture, DDD, CQRS, Vertical Slice, Command Bus,
Event Bus e Dependency Injection.

## Stack

| Camada | Tecnologias |
|--------|-------------|
| Backend | Python 3.13, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (RLS), Redis, **PyJWT** (HS256) |
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

- Tabela `tenants`; seed cria **`universe`** (app) e **`bigbang`** (ops).
- `users`, `roles`, `permissions`, `user_roles` e `role_permissions` são isolados por `tenant_id` com **FORCE ROW LEVEL SECURITY**.
- `tenants` SELECT é restrito ao tenant atual (ou `rls_bypass`); resolução por Host usa a função **`resolve_tenant_by_slug`** (`SECURITY DEFINER`).
- O slug do tenant vem do **subdomínio do Host** (primeiro label) — igual para **qualquer** tenant (`universe`, `bigbang`, …):
  - `universe.localhost` / `bigbang.localhost`
  - `universe.<ip>` / `bigbang.<ip>` (ex.: `bigbang.134.209.122.250`)
  - `universe.lanstar.com.br` / `bigbang.lanstar.com.br`
  - `universe.lanstar.local` / `bigbang.lanstar.local`
- Hosts são validados contra `ALLOWED_TENANT_BASE_DOMAINS` (default: `localhost,lanstar.com.br,lanstar.local`). Formas `*.<ipv4>` são sempre aceitas.
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

### Exposição de rede (Docker)

No `docker-compose.yml`, **Postgres (`5432`) e Redis (`6379`) publicam só em `127.0.0.1`** — não na internet. A API do host (`lanstar-api`) e o nginx usam `localhost`. Containers na rede Compose continuam se falando pelos nomes `postgres` / `redis`.

Não use `"5432:5432"` / `"6379:6379"` (bind em `0.0.0.0`): scanners (ex.: DigitalOcean/Shadowserver) tratam isso como serviço aberto. Em nuvem, complemente com Cloud Firewall bloqueando 5432/6379 de fora.

### Platform Administrator

- Permissões `tenants.*` + `system.settings` existem só no tenant **`bigbang`** (não no RBAC comum).
- API: `GET/POST /api/v1/tenants`, rename, activate/deactivate — exige permissões `tenants.*`.
- `GET /tenants` e `GET /tenants/{id}` incluem o **Administrador** do tenant (usuário com role `ADMIN`: `id`, `username`, `email`, `full_name`), ou `null` se não houver (ex.: tenant `bigbang`).
- `POST /tenants` exige dados do Administrador (`admin_username`, `admin_email`, `admin_full_name`, `admin_password`) e provisiona a role `ADMIN` + permissões RBAC + o usuário admin.
- Login (mesmos padrões de Host do `universe`):
  - http://bigbang.localhost:9000
  - `http://bigbang.<servidor>:9000` (ex.: `http://bigbang.134.209.122.250:9000`)
  - https://bigbang.lanstar.com.br (DNS)
  - http://bigbang.lanstar.local:9000 (`/etc/hosts`)
- Usuário: `galileu` / `123Mudar.`

## Autenticação e autorização

| Peça | Comportamento |
|------|----------------|
| Access token | **PyJWT** HS256 (~15 min), header `Authorization: Bearer`; claim `cv` = `credentials_version` |
| Refresh token | Opaco (`secrets`), Redis guarda só **SHA-256** (TTL 7 dias), cookie **httpOnly** (`lanstar_refresh_token`, `SameSite=lax`, `Secure` fora de development) |
| Frontend | Access só em **memória** (não persiste em `localStorage`); bootstrap/refresh usam o cookie |
| AuthZ | `Depends(require_permission(...))` no backend, resolvido pelo `AuthorizationService` (tenant > entitlement > ACL deny > ACL allow > RBAC > ABAC); UI espelha com `can()` / `meta.permissions` |
| Revogação | Logout e revogação de sessão gravam o `sid` na denylist do Redis — o access token morre na hora, não em 15 min |
| Hierarquia | Roles ranqueadas (`PLATFORM` > `ADMIN` > `MANAGER` > …): quem tem `users.update` / `roles.assign` **não** gerencia pares ou superiores; permissões platform-only não são atribuíveis sem bypass |
| Rate limit | Chave `tenant:IP` via `X-Real-IP` (nginx); login/refresh usam limite mais baixo (`AUTH_RATE_LIMIT_*`) |
| Sessões | Refresh recarrega `role_ids` / `is_active` do banco; senha, desativação, delete ou troca de roles invalida refresh **e** access (`credentials_version`) |
| Senhas | Novas senhas: letra + dígito + caractere especial (mín. 8); troca da própria senha exige `current_password` |

Em produção (`APP_ENV` ≠ `development`):

- `JWT_SECRET_KEY` ≥ 32 caracteres (placeholders rejeitados)
- `ALLOWED_TENANT_BASE_DOMAINS` obrigatório
- Senhas default de banco (`lanstar` / `lanstar_app` / `lanstar_migrate`) rejeitadas na URL — rotacione no Postgres após a migration `0009`
- Seed demo recusado (exceto `SEED_ALLOW_INSECURE=true`)
- `/docs` / OpenAPI desabilitados

## Stack completa (Docker)

```bash
docker compose up -d --build
docker compose --profile seed run --rm seed
```

- App (tenant universe): http://universe.localhost:9000  
  (ou `http://universe.<servidor>:9000` / DNS `universe.lanstar.com.br` / `universe.lanstar.local`)
- Ops (tenant bigbang): http://bigbang.localhost:9000  
  (ou `http://bigbang.<servidor>:9000` / DNS `bigbang.lanstar.com.br` / `bigbang.lanstar.local`)
- API: mesma origem via proxy `/api` (Host preservado)
- Login demo (universe): `admin` ou `admin@lanstar.com.br` / `123Mudar.`

Não use `http://localhost:9000` sem subdomínio — a API exige slug no Host.

Exemplo `/etc/hosts` (ajuste o IP do servidor):

```
127.0.0.1       universe.localhost bigbang.localhost
134.209.122.250 universe.lanstar.local bigbang.lanstar.local
134.209.122.250 universe.134.209.122.250 bigbang.134.209.122.250
```

## Infraestrutura apenas (Postgres + Redis)

```bash
docker compose up -d postgres redis
# ou: sudo systemctl start lanstar-infra
```

Portas no host: `127.0.0.1:5432` (Postgres) e `127.0.0.1:6379` (Redis).

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

Chamadas locais à API devem enviar `Host: universe.localhost` (ex.: curl `-H 'Host: universe.localhost'`).

## Frontend (desenvolvimento local)

```bash
cd frontend
npm install
npm run dev
```

Abra **http://universe.localhost:9000** (proxy `/api` → backend `:8000` com `changeOrigin: false` para preservar o Host).

## Seed

O seed é idempotente. Em `APP_ENV=development` (default local/Docker) cria os dados abaixo.
Fora de development, o seed **recusa** a senha demo salvo `SEED_ALLOW_INSECURE=true`.

Senha demo (`123Mudar.`) atende a política (letra + dígito + especial).

### Tenant `universe`

- permissões de produto (sem `tenants.*` / `system.settings`)
- roles `ADMIN`, `MANAGER`, `OPERATOR`, `CLIENT`, `VIEWER`
- usuários demo (senha `123Mudar.`):

| username | email | role |
|---|---|---|
| `admin` | `admin@lanstar.com.br` | `ADMIN` |
| `manager` | `manager@lanstar.com.br` | `MANAGER` |
| `operator` | `operator@lanstar.com.br` | `OPERATOR` |
| `user` | `user@lanstar.com.br` | `CLIENT` |
| `viewer` | `viewer@lanstar.com.br` | `VIEWER` |

O **ADMIN** (`admin`) é o Administrador do tenant — o mesmo associado em `GET /api/v1/tenants` como `admin`. Tem apenas CRUD de usuários/roles/permissões e `dashboard.admin`.

### Tenant `bigbang`

| username | email | role |
|---|---|---|
| `galileu` | `galileu@lanstar.com.br` | `PLATFORM` |

Sem role `ADMIN` (só `PLATFORM`); em `/tenants` o campo `admin` fica `null` para este tenant.

Permissões: `tenants.create|read|update|activate|deactivate`, `system.settings` e `dashboard.platform`.

```bash
cd backend
python -m scripts.seed
# produção controlada (não recomendado): SEED_ALLOW_INSECURE=true python -m scripts.seed
```

## Testes

```bash
cd backend
pytest -v                                  # tudo
pytest -v -m "not integration"             # só unitários
pytest -v -m integration                   # HTTP + RLS + matriz de autorização (precisa de Postgres e Redis)
pytest --cov=src --cov-report=term-missing # cobertura
python -m bandit -c pyproject.toml -r src  # SAST
pip-audit                                  # dependências
```

Os testes de integração **skipam** automaticamente quando o stack (Postgres/Redis) não está de pé.

## Arquitetura (resumo)

```
Cliente (universe.* | bigbang.*) → FastAPI Gateway
       → TenantMiddleware (Host allowlist → resolve_tenant_by_slug → RLS GUC)
       → RateLimit (tenant:IP)
       → AuthN (PyJWT + reload user / credentials_version) / AuthZ / Validation
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

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [document/AUTHORIZATION.md](document/AUTHORIZATION.md) | Precedência do engine, códigos, bundles, regras para quem escreve rota |
| [document/ACL.md](document/ACL.md) | ACL por recurso: modelo, avaliação, API, boas práticas |
| [document/SERVICE_HUB.md](document/SERVICE_HUB.md) | Contrato de Service Slice, entitlements, quotas, medição |
| [document/SECURITY.md](document/SECURITY.md) | Tokens, denylist, headers, isolamento, segredos, auditoria, supply chain |
| [document/0002-sistema-iam.md](document/0002-sistema-iam.md) | Panorama do IAM e histórico do roadmap |
