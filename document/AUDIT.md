# HubSuite — Auditoria (Accounting)

Rastro durável do que aconteceu: quem, o quê, em qual recurso, de qual IP, em qual request. É a letra **A** de Accounting em [AAA.md](AAA.md).

| | |
|---|---|
| **Tabela** | `audit_events` — [iam/models.py](../backend/src/modules/iam/models.py) |
| **Serviço** | [iam/audit/service.py](../backend/src/modules/iam/audit/service.py) |
| **EventBus → log + DB** | [audit_handlers.py](../backend/src/shared/infrastructure/audit_handlers.py) |
| **Negativas AuthZ** | `AUTHZ_DENIED` em [authorization_adapters.py](../backend/src/shared/infrastructure/security/authorization_adapters.py) |
| **Correlação** | [request_id_middleware.py](../backend/src/shared/infrastructure/request_id_middleware.py) |

---

## 1. Modelo

| Coluna | Conteúdo |
|--------|----------|
| `tenant_id` | RLS forçado — um tenant não lê o audit do outro |
| `actor_user_id` / `actor_type` | usuário ou `system` |
| `action` | nome do evento (`UserLoggedIn`, `AUTHZ_DENIED`, …) |
| `resource_type` / `resource_id` | alvo, quando houver |
| `ip_address` / `user_agent` | ambiente |
| `request_id` | mesmo id do header `X-Request-ID` / resposta |
| `payload` | JSONB — **sem secrets** (senhas, refresh, API keys) |
| `created_at` | timestamptz |

---

## 2. Como entra um evento

Dois caminhos, os dois tenant-scoped:

1. **Domain Event** (login, logout, refresh, CRUD de users/roles/permissions) → `vizion.audit` no stdout **e** insert em `audit_events` quando há sessão.
2. **Engine** → toda `Decision.denied` vira `AUTHZ_DENIED` com `stage`, `reason`, ação, recurso, IP, `request_id`.

`RequestIdMiddleware` lê `X-Request-ID` ou gera um, guarda em `ContextVar` e devolve no response. Um incidente reconstrói-se ligando access log ↔ audit pelo mesmo id.

---

## 3. API

| Método | Rota | Permissão |
|--------|------|-----------|
| `GET` | `/api/v1/audit-events?action=&request_id=&limit=&offset=` | `iam.audit.read` |

Limite máximo 200. Ordenação: mais recente primeiro. Filtros opcionais por `action` e `request_id`.

---

## 4. Retenção

`AUDIT_RETENTION_DAYS` (default **365**). A função SQL `prune_audit_events(integer)` (migration 0017) apaga em um statement, **cross-tenant** — o caller precisa de `rls_bypass`.

```bash
cd backend && python -m scripts.prune_audit
```

Agende no cron/systemd do ambiente. Sem o job, a tabela cresce sem teto.

---

## 5. O que não vai para o payload

Refresh token, senha, secret de client OAuth, API key em claro, recovery codes, cookie. `AUTHZ_DENIED` registra estágio e motivo, não o JWT.

Alertas operacionais recomendados (fora do código): rajada de login falho, pico de `AUTHZ_DENIED`, prune que não roda.
