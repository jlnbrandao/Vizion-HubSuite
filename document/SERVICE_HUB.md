# Vizion — Hub de Serviços (contrato de Service Slice)

Como um serviço novo (GPS, SNMP, DDNS, ERP, Imobiliária, Geoprocessamento…) entra no Vizion sem alterar o núcleo. O Hub fornece identidade, autorização, isolamento por tenant, auditoria, entitlements e quotas; o serviço fornece apenas o próprio domínio.

| | |
|---|---|
| **Catálogo** | tabela `services` (`slug`, `namespace`, `version`, `is_core`, `default_quotas`) |
| **Contrato por tenant** | tabela `tenant_services` (`plan`, `status`, `quotas`, `expires_at`) — RLS |
| **Medição** | tabela `usage_records` + `GET /api/v1/usage` (ver seção 5) |
| **Esqueleto** | [backend/src/modules/_template_service/](../backend/src/modules/_template_service) |
| **Catálogo declarativo** | [backend/src/modules/services/catalog.py](../backend/src/modules/services/catalog.py) |

---

## 1. Conceitos

- **Serviço** — unidade vendável, dona de um namespace de permissões (`gps.*`).
- **Core vs. default** — `is_core` marca o que é o próprio Hub (`iam`, `platform`) e **não** pode ser desligado para nenhum tenant. `enabled_by_default` marca o que já vem contratado ao criar o tenant (`iam`, `platform`, `integration`) mas **pode** ser suspenso. `integration` é vendável: entra ligado, sai quando o contrato termina.
- **Entitlement** — o tenant contratou o serviço. Status que autorizam: `active` e `trial`. Status que bloqueiam: `suspended` e `disabled`.
- **Plano e quotas** — `plan` é rótulo comercial; `quotas` é JSONB com os limites efetivos. `tenant_services.quotas` sobrepõe `services.default_quotas` chave por chave.

O engine de autorização checa o entitlement **antes** do RBAC (ver [AUTHORIZATION.md](AUTHORIZATION.md)). Sem contrato, nenhuma permissão do namespace autoriza nada — e o slice desaparece do menu e das rotas do SPA.

---

## 2. Contrato do Service Slice

### 2.1 Backend

1. **Pacote vertical** em `backend/src/modules/<slug>/`: `models.py`, `service.py`, `routes.py` (+ `handlers/`, `queries/` quando houver CQRS). Nada de espalhar o serviço pelas camadas do núcleo.
2. **Namespace próprio** de permissões, declarado em [permission_codes.py](../backend/src/shared/infrastructure/security/permission_codes.py) no formato `service.resource.action`. O recurso precisa existir em `SERVICE_BY_RESOURCE`. Nunca declarar código de outro serviço.
3. **Registro no catálogo**: entrada em `CORE_SERVICES` (serviços do Hub) ou linha em `services` via migration/seed. `namespace` = prefixo das permissões.
4. **Toda tabela é tenant-scoped**: coluna `tenant_id`, `ENABLE`/`FORCE ROW LEVEL SECURITY` e a policy padrão de isolamento (copiar de [0016_service_catalog.py](../backend/alembic/versions/0016_service_catalog.py)); `GRANT` para `vizion_app`.
5. **Autorização só via engine**: `Depends(require_permission("<slug>.<recurso>.<ação>"))` nas rotas e `AuthorizationService.authorize(...)` para decisões por recurso. O slice não reimplementa hierarquia, ACL nem ABAC.
6. **Medição do que é vendido**: `ServiceQuotaGuard.enforce(tenant_id=..., namespace=..., metric=...)` na entrada da operação tarifada.
7. **Auditoria** de mudanças de estado via `AuditService` (o engine já registra `AUTHZ_DENIED`).
8. **Router** incluído em [main.py](../backend/src/main.py) com prefixo `/api/v1` e módulo adicionado a `_WIRE_MODULES`.

### 2.2 Frontend

1. Slice em `frontend/src/modules/<slug>/` com `routes.ts`, `pages/`, `components/`.
2. Cada rota declara `meta.service` (slug) e `meta.permissions` (códigos gerados). O guard global recusa serviço não contratado antes de olhar permissão.
3. Constantes **apenas** as geradas em `constants/permissions.ts` (`cd backend && python -m scripts.generate_frontend_permissions`). Nunca string literal de permissão.
4. Entradas de menu são declaradas no backend, em [navigation/catalog.py](../backend/src/modules/navigation/catalog.py). O SPA só renderiza o que `GET /api/v1/navigation` devolve.

### 2.3 Checklist de aceite

- [ ] `services` tem a linha do serviço com namespace correto
- [ ] permissões só do próprio namespace, catálogo regenerado no frontend
- [ ] todas as tabelas com `tenant_id` + RLS forçado + policy de isolamento
- [ ] rotas protegidas por `require_permission`, sem checagem manual de role
- [ ] operações tarifadas passando por `ServiceQuotaGuard`
- [ ] eventos de auditoria nas mutações
- [ ] menu declarado no catálogo de navegação
- [ ] testes: RBAC feliz, RBAC negado, tenant A não vê dados de B, serviço suspenso nega

---

## 3. API

| Método | Rota | Permissão | Uso |
|--------|------|-----------|-----|
| `GET` | `/api/v1/services/me` | autenticado | serviços do próprio tenant (status, plano, quotas) |
| `GET` | `/api/v1/services` | `platform.services.read` | catálogo completo do Hub |
| `GET` | `/api/v1/services/tenants/{tenant_id}` | `platform.services.read` | contratos de um tenant |
| `PUT` | `/api/v1/services/tenants/{tenant_id}/{slug}` | `platform.services.manage` | ligar, suspender, replanejar, quotar |

`GET /api/v1/auth/me` e `GET /api/v1/navigation` devolvem `services[]` = serviços contratados **∩** serviços em que o usuário tem alguma permissão. É essa lista que o SPA usa para esconder slices inteiros.

Alterar um contrato invalida o cache de entitlements do engine (TTL curto, ~30s) na mesma requisição.

---

## 4. Ciclo de vida de um tenant

1. `CreateTenantHandler` cria o tenant, chama `ensure_default_services` (os `enabled_by_default` do catálogo) e provisiona a role ADMIN + usuário administrador.
2. `scripts/seed.py` registra o catálogo (`_ensure_service_catalog`, sincronizando também as flags `is_core`) e entitla os serviços default de cada tenant semeado.
3. A migration [0016](../backend/alembic/versions/0016_service_catalog.py) faz o backfill dos tenants que já existiam — nenhum tenant perde acesso na atualização. A [0018](../backend/alembic/versions/0018_service_core_flags.py) corrige as flags `is_core` em bases já implantadas, deixando `integration` suspensível.

---

## 5. Medição (accounting)

O que é vendido precisa ser contável. `ServiceQuotaGuard.enforce(...)` faz as duas coisas na mesma chamada: aplica a quota do contrato e registra o consumo.

| Peça | Detalhe |
|------|---------|
| Tabela | `usage_records` (`tenant_id`, `service`, `metric`, `granularity`, `period_start`, `quantity`) — RLS, upsert por período |
| Granularidade | `day` (default) e `month` |
| Métrica padrão | `requests_per_minute` como contador de operações; serviços podem registrar métricas próprias |
| Leitura do tenant | `GET /api/v1/usage` — `platform.usage.read` |
| Leitura da plataforma | `GET /api/v1/usage/tenants/{tenant_id}` — `platform.usage.read_all` (bypass de RLS controlado) |
| UI | [modules/platform/pages/UsagePage.vue](../frontend/src/modules/platform/pages/UsagePage.vue) |

Falha ao medir nunca derruba a operação do cliente; a quota, sim, é hard-fail (HTTP 429).

---

## 6. Fora do escopo

GPS, SNMP, DDNS e ERP **não** são implementados aqui: este documento é o encaixe. O que existe hoje são os serviços do Hub (`iam`, `platform`) mais `integration` como serviço vendável, e o esqueleto `_template_service`, que não é registrado em `main.py`.
