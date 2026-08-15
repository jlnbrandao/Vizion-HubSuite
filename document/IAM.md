# HubSuite — IAM (Identity and Access Management)

Quem o usuário é, como prova isso e o que o Hub faz com essa identidade. Autorização detalhada está em [AUTHORIZATION.md](AUTHORIZATION.md); o trio AuthN / AuthZ / Accounting em [AAA.md](AAA.md).

| | |
|---|---|
| **Produto** | HubSuite (runtime / pacote `vizion`) |
| **Módulo** | [backend/src/modules/iam/](../backend/src/modules/iam/) |
| **AuthN** | [backend/src/modules/authentication/](../backend/src/modules/authentication/) |
| **Engine AuthZ** | [security/authorization.py](../backend/src/shared/infrastructure/security/authorization.py) |
| **Roadmap histórico** | [0001-sistema-iam.md](0001-sistema-iam.md) |

---

## 1. O que o IAM cobre

| Pergunta | Nome | Documento |
|----------|------|-----------|
| Quem é você? | Identity / Authentication | este + [AAA.md](AAA.md) |
| O que pode fazer? | Authorization | [AUTHORIZATION.md](AUTHORIZATION.md), [RBAC.md](RBAC.md), [ABAC.md](ABAC.md), [ACL.md](ACL.md) |
| Em qual contexto? | Tenant, sessão, dispositivo | [MULTI_TENANT.md](MULTI_TENANT.md), [RLS.md](RLS.md) |
| O que aconteceu? | Accounting / audit | [AUDIT.md](AUDIT.md) |

Há dois níveis de maturidade. O HubSuite opera nos dois, com escopos diferentes:

| Nível | Significado | No código |
|-------|-------------|-----------|
| **IAM de aplicação** | Login, usuários, papéis e permissões **dentro** do produto | tenant `universe` |
| **IAM plataforma** | Catálogo de tenants, IdP (OIDC/OAuth), SCIM, federação, M2M | tenant `ows` (OpenVizion Web Service) |

---

## 2. Arquitetura

```
SPA (HubSuite)                 nginx / FastAPI
  cookie httpOnly (refresh)  →  TenantMiddleware (Host → slug)
  Bearer access (memória)    →  JWT + cv + sid denylist
                             →  AuthorizationService
                             →  PostgreSQL FORCE RLS + Redis
```

O **primeiro label do Host** define o tenant. Não há seletor de tenant no login. O JWT carrega `tenant_id` / `tenant_slug` e é rejeitado se o Host for de outro tenant. Ver [MULTI_TENANT.md](MULTI_TENANT.md).

---

## 3. Superfície HTTP

Prefixo da API: `/api/v1`. Rotas IAM em [iam/routes.py](../backend/src/modules/iam/routes.py).

| Área | Rotas (resumo) |
|------|----------------|
| Sessão | `POST /auth/login`, `/auth/refresh`, `/auth/logout`; `GET /auth/me` |
| Ciclo de vida | convite, forgot/reset password, políticas de senha (`/auth-policies`) |
| MFA | TOTP enroll/confirm/verify, WebAuthn register |
| Sessões | `GET /sessions`, revoke uma / todas / por usuário |
| Audit | `GET /audit-events` |
| ACL | `GET/POST /acls`, `DELETE /acls/{id}` |
| ABAC | `GET/POST /access-policies` |
| OIDC/OAuth | `/.well-known/openid-configuration`, `/jwks.json`, clients, consent, token, userinfo |
| Máquina | service accounts, API keys |
| Federação | identity providers, SSO start, SAML ACS |
| SCIM | módulo [iam/scim/](../backend/src/modules/iam/scim/) |

UI correspondente: `frontend/src/modules/iam/`.

---

## 4. Identidade no token vs no `/me`

O access JWT é **enxuto**: `sub`, `tenant_id`, `tenant_slug`, `cv`, `sid`, `amr`, `acr`, `iat`, `exp`. Sem e-mail, nome ou roles.

`GET /auth/me` devolve identidade, roles, permissões efetivas (roles + bundles) e serviços contratados. A SPA hidrata o Pinia a partir daí.

---

## 5. Seed

| Tenant | Slug | Host local | Papel demo |
|--------|------|------------|------------|
| Universe (produto) | `universe` | `universe.localhost` | `admin` / `ADMIN` |
| OpenVizion Web Service (ops) | `ows` | `ows.localhost` | `root` / `PLATFORM` |

E-mails demo: `@openvizion.com`. Senha demo: `123Mudar.` (somente `APP_ENV=development` ou `SEED_ALLOW_INSECURE=true`).

---

## 6. Mapa de documentos

| Documento | Assunto |
|-----------|---------|
| [AAA.md](AAA.md) | Authentication, Authorization, Accounting |
| [RBAC.md](RBAC.md) | Roles, códigos, bundles, hierarquia |
| [ABAC.md](ABAC.md) | Políticas contextuais (`access_policies`) |
| [ACL.md](ACL.md) | Exceção por recurso |
| [AUTHORIZATION.md](AUTHORIZATION.md) | Precedência única do engine |
| [MULTI_TENANT.md](MULTI_TENANT.md) | Host, JWT, tenants de seed |
| [RLS.md](RLS.md) | FORCE RLS, GUCs, roles de banco |
| [AUDIT.md](AUDIT.md) | `audit_events`, `request_id`, retenção |
| [SECURITY.md](SECURITY.md) | Tokens, cookies, headers, segredos, SAST |
| [SERVICE_HUB.md](SERVICE_HUB.md) | Entitlements, quotas, fatias de serviço |
