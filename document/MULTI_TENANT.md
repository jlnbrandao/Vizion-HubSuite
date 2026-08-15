# HubSuite — Multi-tenant

O tenant **não** é um campo do login. Ele vem do **Host**. Um token emitido em `universe.localhost` é lixo em `ows.localhost`, mesmo com assinatura válida.

| | |
|---|---|
| **Resolução** | [tenant_host.py](../backend/src/shared/infrastructure/tenant_host.py) + [tenant_middleware.py](../backend/src/shared/infrastructure/security/tenant_middleware.py) |
| **Tabela** | `tenants` |
| **Função SQL** | `resolve_tenant_by_slug` (`SECURITY DEFINER`) |
| **Seed** | [scripts/seed.py](../backend/scripts/seed.py) |
| **RLS** | [RLS.md](RLS.md) |

---

## 1. Resolução pelo Host

O slug é o **primeiro label**:

| Host | Slug |
|------|------|
| `universe.localhost` | `universe` |
| `ows.localhost:9000` | `ows` |
| `ows.openvizion.com` | `ows` |
| `universe.134.209.122.250` | `universe` |

Rejeitados: `localhost` sem subdomínio, IP nu, `www.openvizion.com`, `api.openvizion.com` (primeiro label reservado / sem tenant).

Sufixos aceitos: `ALLOWED_TENANT_BASE_DOMAINS` (default `localhost,openvizion.com,openvizion.local`). Formas `*.<ipv4>` são sempre aceitas. Fora de development a allowlist é **obrigatória**.

Tenant desconhecido → **404** `Unknown tenant: {slug}` **antes** do login. Por isso `ows.localhost` falha se o banco ainda tiver o slug antigo `vws` — rode o seed.

---

## 2. Tenants do seed

UUID estáveis (o seed **renomeia** slug/nome no refresh):

| UUID | Slug | Nome | Função |
|------|------|------|--------|
| `a0000000-…0001` | `universe` | Universe | produto (RBAC comum) |
| `a0000000-…0002` | `ows` | OpenVizion Web Service | ops / PLATFORM |

Histórico do ops: `platform` → `bigbang` → `vws` → `ows`. Alembic `0008` ainda insere o slug histórico `bigbang`; o seed corrige.

`/etc/hosts` local:

```
127.0.0.1    universe.localhost ows.localhost
```

---

## 3. Quatro camadas de isolamento

Na ordem em que atuam:

1. **Host → tenant.** Middleware resolve o slug e faz bind no `ContextVar`.
2. **Token vs Host.** JWT com `tenant_id` / `tenant_slug` de outro tenant → 401.
3. **Engine.** Estágio `TENANT` é hard-fail. ACL e ABAC **não** sobrepõem.
4. **RLS.** `FORCE ROW LEVEL SECURITY`; a API conecta como `vizion_app` (sem `BYPASSRLS`).

Repositórios SQLAlchemy também filtram por `tenant_id` (defense-in-depth).

---

## 4. Plataforma vs produto

| | `universe` | `ows` |
|---|------------|-------|
| Roles | ADMIN…VIEWER | PLATFORM |
| Permissões platform-only | ausentes | `tenants.*`, `services.*`, `usage.read_all`, … |
| Login demo | `admin` / `123Mudar.` | `root` / `123Mudar.` |
| Host | `universe.localhost` | `ows.localhost` |

Listar/criar tenants exige `rls_bypass` pontual + permissão `tenants.*`. O bypass é `try/finally` e não vira default da conexão. Ver [RLS.md](RLS.md).

---

## 5. Provisionamento

`POST /api/v1/tenants` (PLATFORM) cria a linha, a role `ADMIN`, o catálogo RBAC de produto, o usuário Administrador e os entitlements default. O Administrador aparece em `GET /tenants` como `admin` (ou `null` no tenant `ows`).

Testes: [test_tenant_isolation.py](../backend/tests/integration/test_tenant_isolation.py), [test_tenant_host.py](../backend/tests/unit/shared/test_tenant_host.py).
