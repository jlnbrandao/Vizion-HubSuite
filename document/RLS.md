# HubSuite — RLS (Row Level Security)

A última linha de isolamento. Mesmo que o engine erre, a conexão da API **não enxerga** linha de outro tenant.

| | |
|---|---|
| **GUCs** | `app.current_tenant_id`, `app.rls_bypass` — [sqlalchemy_unit_of_work.py](../backend/src/shared/infrastructure/sqlalchemy_unit_of_work.py) |
| **Context** | [tenant_context.py](../backend/src/shared/infrastructure/tenant_context.py) |
| **Migration base** | [0008_tenants_rls.py](../backend/alembic/versions/0008_tenants_rls.py), [0009_tenant_security.py](../backend/alembic/versions/0009_tenant_security.py) |
| **Prova** | [test_rls_policies.py](../backend/tests/integration/test_rls_policies.py) (conecta como `vizion_app`) |

Complementa [MULTI_TENANT.md](MULTI_TENANT.md); não substitui o estágio `TENANT` do engine.

---

## 1. Policy padrão

Toda tabela tenant-scoped recebe `ENABLE` + **`FORCE` ROW LEVEL SECURITY** e uma policy no formato:

```sql
USING (
  current_setting('app.rls_bypass', true) = 'on'
  OR tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
)
WITH CHECK ( /* o mesmo */ )
```

`FORCE` vale inclusive para o **owner** da tabela. Sem isso, o papel `vizion` (superuser/owner no Compose) leria tudo; a API não usa esse papel em runtime.

`tenants` é especial: SELECT só da linha do tenant atual (ou bypass). A resolução por slug usa `resolve_tenant_by_slug(text)` — `SECURITY DEFINER`, `search_path = public` — porque o middleware precisa achar o tenant **antes** de setar o GUC.

---

## 2. Como a API liga o contexto

Ao entrar no Unit of Work:

```sql
SELECT set_config('app.rls_bypass', 'on'|'off', true);          -- SET LOCAL
SELECT set_config('app.current_tenant_id', '<uuid>'|'', true);
```

Os valores vêm dos `ContextVar` preenchidos pelo `TenantMiddleware` (e, pontualmente, por `bind_rls_bypass`).

Sem `current_tenant_id` e sem bypass, a policy não casa nenhuma linha — o handler vê conjunto vazio, não um vazamento.

---

## 3. Roles de banco

| Role | Uso | BYPASSRLS |
|------|-----|-----------|
| `vizion` | Owner / Alembic / seed (`DATABASE_MIGRATE_URL`) | efetivo (owner; FORCE ainda aplica, seed usa bypass) |
| `vizion_app` | API (`DATABASE_URL`) | **não** |
| `vizion_migrate` | jobs privilegiados opcionais | sim |

Senhas default (`vizion` / `vizion_app` / `vizion_migrate`) são **recusadas** fora de development. Rode a API sempre como `vizion_app`.

---

## 4. Bypass

`bind_rls_bypass(True)` existe para:

- catálogo de tenants (PLATFORM)
- entitlements / usage cross-tenant (`usage.read_all`)
- seed e prune de audit

Regras: pontual, `try/finally`, permissão platform-only na rota. Nunca deixar a conexão da API com bypass permanente.

---

## 5. Tabelas cobertas

Além de `users`, `roles`, `permissions` e associações (0008), as migrations seguintes aplicam a mesma policy + `GRANT` a `vizion_app` em: sessões, audit, convites, ACL, bundles, `access_policies`, integrações, webhooks, `tenant_services`, `usage_records`, etc.

Fatia nova de serviço: copiar o bloco de [0016_service_catalog.py](../backend/alembic/versions/0016_service_catalog.py) — coluna `tenant_id`, `FORCE RLS`, policy, `GRANT`. Contrato em [SERVICE_HUB.md](SERVICE_HUB.md).

---

## 6. Defense-in-depth

Repositórios SQLAlchemy adicionam `WHERE tenant_id = :current` mesmo com RLS ligado. Os dois mecanismos precisam falhar juntos para vazar dado. Teste de integração HTTP: [test_tenant_isolation.py](../backend/tests/integration/test_tenant_isolation.py).
