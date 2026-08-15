# HubSuite — AAA (Authentication, Authorization, Accounting)

AAA é o recorte clássico de controle de acesso. No HubSuite as três letras são módulos distintos que se encontram no request.

| Letra | Pergunta | Onde |
|-------|----------|------|
| **Authentication** | A identidade é verdadeira? | [authentication/](../backend/src/modules/authentication/), MFA, federação |
| **Authorization** | Esta identidade pode fazer *isto* neste recurso? | [AuthorizationService](../backend/src/shared/infrastructure/security/authorization.py) |
| **Accounting** | O que aconteceu, quem fez, quando? | [AUDIT.md](AUDIT.md) |

Visão de produto: [IAM.md](IAM.md). Isolamento: [MULTI_TENANT.md](MULTI_TENANT.md) + [RLS.md](RLS.md).

---

## 1. Authentication (AuthN)

Prova de identidade **dentro do tenant do Host**. Credenciais de `universe` não autenticam em `ows.localhost`.

| Mecanismo | Comportamento |
|-----------|----------------|
| Senha | Username **ou** e-mail + bcrypt (`PasswordHasher`) |
| MFA | TOTP e WebAuthn; obrigatório para roles em `IAM_MFA_REQUIRED_ROLES` (default `ADMIN,PLATFORM`) |
| Refresh | Cookie `httpOnly` + token opaco no Redis (SHA-256); rotação a cada uso |
| Federação | OIDC / SAML SP (`/auth/sso/...`) |
| Máquina | Service accounts + API keys (secret visível só na criação) |
| OIDC como IdP | O Hub emite tokens RS256 para clients (`/oauth/token`, JWKS) |

Fluxo de senha:

```
POST /auth/login  (Host = tenant)
  → valida no tenant atual
  → se MFA exigido: mfa_token de curta duração
  → senão: access JWT + refresh (Redis + cookie + sinal vizion_has_session)
  → UserLoggedInEvent → audit
```

Revogação: `cv` no JWT + denylist de `sid` no Redis. Detalhe em [SECURITY.md](SECURITY.md).

O frontend **não** persiste o access token. `bootstrap()` só chama `/auth/refresh` se existir o cookie-sinal `vizion_has_session`.

---

## 2. Authorization (AuthZ)

Um único ponto de decisão. Rotas usam `Depends(require_permission(...))` ou `AuthorizationService.authorize(..., resource=...)`.

Precedência fixa (não configurável):

1. Tenant  
2. Entitlement  
3. ACL deny  
4. ACL allow  
5. RBAC  
6. ABAC (só nega)

Documento canônico: [AUTHORIZATION.md](AUTHORIZATION.md). Recortes: [RBAC.md](RBAC.md), [ACL.md](ACL.md), [ABAC.md](ABAC.md).

Guard de UI (`can()` / `meta.permissions`) é UX. A barreira é o backend + RLS.

---

## 3. Accounting

Toda mutação relevante e toda negativa de autorização deixam rastro:

| Canal | Uso |
|-------|-----|
| Log `vizion.audit` | stdout estruturado (EventBus) |
| Tabela `audit_events` | persistência tenant-scoped, RLS |
| `X-Request-ID` | correlação log ↔ audit ↔ resposta HTTP |

`AUTHZ_DENIED` grava estágio e motivo, sem secrets. Consulta: `GET /api/v1/audit-events`. Retenção: [AUDIT.md](AUDIT.md).

---

## 4. Ordem no request

```
RequestIdMiddleware
  → TenantMiddleware          (AuthN de tenant: Host → slug)
  → decode JWT + cv + sid     (AuthN de usuário)
  → require_permission        (AuthZ)
  → handler + FORCE RLS       (isolamento de dados)
  → EventBus / AUTHZ_DENIED   (Accounting)
```

As três letras falham fechadas: tenant desconhecido → 404; credencial inválida → 401; permissão insuficiente → 403; linha de outro tenant → invisível no SQL.
