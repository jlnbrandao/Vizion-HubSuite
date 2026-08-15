# Lanstar — Sistema IAM (Identity and Access Management)

Documento de referência do modelo de identidade e acesso do **enterprise-template** (produto Lanstar): o que já existe hoje, como funciona, o que falta para um IAM completo e o roadmap para torná-lo um **Identity Provider** multi-tenant.

| | |
|---|---|
| **Produto** | Lanstar — Enterprise Template |
| **Escopo** | Autenticação, autorização, multi-tenancy, evolução para IdP |
| **Stack** | FastAPI, PostgreSQL (RLS), Redis, Vue 3 / Quasar, PyJWT |
| **Status atual** | IAM de **aplicação** + plataforma (fases 0–8 implementadas no código) |
| **Alvo** | IAM **plataforma** (OIDC/OAuth IdP + MFA + SCIM + ABAC + …) — em evolução contínua |

---

## 1. O que é IAM neste contexto

**IAM (Identity and Access Management)** responde a três perguntas:

1. **Quem é você?** — Identity / Authentication (AuthN)
2. **O que você pode fazer?** — Authorization (AuthZ)
3. **Em qual contexto?** — Tenant, sessão, dispositivo, aplicativo cliente, horários, etc.

Há dois níveis de maturidade:

| Nível | Significado | Exemplo |
|-------|-------------|---------|
| **IAM de aplicação** | Login, usuários, papéis e permissões **dentro** de um produto | O que o Lanstar é **hoje** |
| **IAM plataforma (IdP)** | Outros sistemas autenticam **nele**; federação, SCIM, consent, M2M | Keycloak, Auth0, Cognito — **alvo** deste roadmap |

O Lanstar já resolve bem o primeiro nível. O roadmap descrito neste documento eleva o projeto ao segundo.

---

## 2. Visão geral da arquitetura atual

```
┌─────────────┐     Host: {tenant}.domínio      ┌──────────────────────────────┐
│  Vue/Quasar │ ──────────────────────────────► │  nginx / API Gateway         │
│  (SPA)      │   cookie httpOnly (refresh)     │  TenantMiddleware             │
│             │   Bearer access (memória)       │  RateLimit → CORS → Routes   │
└─────────────┘                                 └──────────────┬───────────────┘
                                                               │
                    ┌──────────────────────────────────────────┼────────────────┐
                    │                                          ▼                │
                    │  Authentication   Users   Roles   Permissions   Tenants   │
                    │       │             │       │          │            │     │
                    │       └─────────────┴───────┴──────────┴────────────┘     │
                    │                         │                                 │
                    │              CommandBus / QueryBus / EventBus              │
                    │                         │                                 │
                    │         ┌───────────────┴───────────────┐                 │
                    │         ▼                               ▼                 │
                    │   PostgreSQL (RLS)                   Redis                │
                    │   users, roles, perms, tenants       refresh tokens       │
                    │   FORCE ROW LEVEL SECURITY           rate limit           │
                    └───────────────────────────────────────────────────────────┘
```

**Ideia central:** o **subdomínio do Host** define o tenant. Não há seletor de tenant no login. O JWT carrega `tenant_id` / `tenant_slug` e é rejeitado se o Host for de outro tenant.

---

## 3. O que já está implementado

### 3.1 Autenticação (AuthN)

| Peça | Comportamento |
|------|----------------|
| Login | Username **ou** e-mail + senha (bcrypt) |
| Access token | JWT **HS256**, ~15 min, header `Authorization: Bearer` |
| Refresh token | Opaco (`secrets`), armazenado no Redis só como **SHA-256**, TTL ~7 dias |
| Cookie | `lanstar_refresh_token`, **httpOnly**, `SameSite=lax`, `Secure` fora de development, prefixo `__Host-` em produção |
| Frontend | Access token **somente em memória** (não vai para `localStorage`) |
| Logout | Invalida o refresh **e** grava o `sid` na denylist do Redis — o access morre na hora |
| Invalidação forte | Campo `credentials_version` (`cv` no JWT): sobe em troca de senha, desativação, delete ou mudança de roles — access antigo é rejeitado e refreshes do usuário são apagados |

**Claims do access token:** `sub`, `tenant_id`, `tenant_slug`, `cv`, `sid`, `amr`, `acr`, `iat`, `exp`. O token **não** carrega e-mail, nome ou roles: identidade, permissões e serviços contratados vêm de `GET /api/v1/auth/me`.

**Endpoints:** `POST /api/v1/auth/login`, `/refresh`, `/logout`; `GET /api/v1/auth/me`.

Detalhes de headers, denylist, segredos e supply chain: [SECURITY.md](SECURITY.md).

### 3.2 Autorização (AuthZ) — RBAC + ACL + ABAC

Modelo:

```
Permission (service.resource.action)
        ↑
 PermissionBundle ⇄ Permissions
        ↑
   Role ⇄ Bundles (+ permissões finas)
        ↑
   User ⇄ Roles          ⟂  ACL por recurso (allow/deny)
```

- Decisão **única** no `AuthorizationService`, com precedência fixa: tenant > entitlement > ACL deny > ACL allow > RBAC > ABAC. Documento dedicado: [AUTHORIZATION.md](AUTHORIZATION.md).
- Códigos canônicos em `backend/src/shared/infrastructure/security/permission_codes.py`, namespaced como `service.resource.action`, com alias legado `resource.action` aceito. O espelho do frontend é **gerado** (`python -m scripts.generate_frontend_permissions`).
- Backend: `Depends(require_permission(...))` — valida JWT, tenant do Host, usuário ativo, `cv`, `sid` não revogado, e delega ao engine.
- Frontend: `can()` / `canAny()` / `meta.permissions` / `meta.service` nas rotas (espelho de UX; a barreira real é o backend).
- **Hierarquia de roles:** `PLATFORM` > `ADMIN` > `MANAGER` > `OPERATOR` > `CLIENT` > `VIEWER`, definida em `HierarchyPolicy` dentro do engine. Quem gerencia usuários/roles **não** pode gerenciar pares ou superiores.
- Permissões **platform-only** (`tenants.*`, `services.*`, `usage.read_all`, `system.settings`, `dashboard.platform`, `integration.*`) existem só no tenant de operações (`bigbang`), não no RBAC comum de produto.
- Exceções por recurso ficam em `resource_acls` ([ACL.md](ACL.md)); políticas contextuais (Casbin) podem **negar** o que o RBAC concedeu.

### 3.3 Multi-tenancy e isolamento

| Elemento | Detalhe |
|----------|---------|
| Tabela `tenants` | Isolamento lógico; seed cria `universe` (app) e `bigbang` (ops) |
| Resolução | Primeiro label do Host → slug → tenant (`universe.localhost`, `bigbang.lanstar.com.br`, …) |
| RLS | `FORCE ROW LEVEL SECURITY` em toda tabela tenant-scoped (users, roles, permissions e associações, audit, sessões, ACLs, bundles, `tenant_services`, `usage_records`, integrações) |
| Defense-in-depth | Repositórios SQLAlchemy também filtram por `tenant_id` |
| Roles de banco | `lanstar` (migrate/owner), `lanstar_app` (API, sujeita a RLS), `lanstar_migrate` (opcional, `BYPASSRLS`) |

### 3.4 Sessões e rate limiting

- Refresh recarrega `role_ids` / `is_active` do banco a cada renovação.
- Sessões em `auth_sessions` (`sid` no token), listáveis e revogáveis; revogar grava o `sid` na denylist do Redis.
- Rate limit Redis por `tenant:IP` (`X-Real-IP`); login/refresh com limite mais baixo que a API geral. Quotas por `tenant+serviço` no `ServiceQuotaGuard`.
- Eventos de domínio (login, logout, CRUD de users/roles/permissions, `AUTHZ_DENIED`) vão para log estruturado (`lanstar.audit`) **e** para `audit_events`, consultável em `GET /api/v1/audit-events` e correlacionável por `request_id`.

### 3.5 Ciclo de vida

- CRUD de usuários, roles, permissões e bundles
- Troca de senha (com `current_password` quando for a própria)
- Ativar / desativar usuário (com invalidação de sessão)
- Provisionamento de tenant + admin + entitlements default
- Convite por e-mail e forgot/reset password (SMTP opcional; em development o token vai para o log)
- MFA TOTP e WebAuthn com recovery codes
- SSO/federação (OIDC e SAML SP), SCIM 2.0, service accounts e API keys
- OAuth/OIDC como provedor, com consent e JWKS RS256

### 3.6 Catálogo de permissões

Fonte de verdade: `permission_codes.py` (canônico + alias legado), exposto em `GET /api/v1/permissions/catalog`.

| Serviço | Recursos |
|---------|----------|
| `iam` | `users`, `roles`, `permissions`, `permission_groups`, `dashboard`, `system`, `audit`, `sessions`, `oauth_clients`, `service_accounts`, `api_keys`, `federation`, `policies`, `acl`, `scim` |
| `platform` | `tenants`, `services`, `usage` |
| `integration` | `integration` |

Bundles semeados: `iam.admin`, `iam.manager`, `iam.operator`, `iam.client`, `iam.viewer`, `platform.admin`, `integration.admin`. Roles compõem bundles; `role_permissions` continua para exceções finas.

### 3.7 Roles seed

**Tenant `universe` (produto):** `ADMIN`, `MANAGER`, `OPERATOR`, `CLIENT`, `VIEWER`.

**Tenant `bigbang` (plataforma):** `PLATFORM` (usuário demo `galileu`).

---

## 4. Fluxos atuais (resumo)

### 4.1 Login

```
Usuário → POST /login (Host = tenant)
       → valida credenciais no tenant atual
       → emite access JWT + refresh (Redis + cookie)
       → publica UserLoggedInEvent (audit log)
```

### 4.2 Request autenticado

```
Request + Bearer + Host
  → RequestIdMiddleware liga o request_id
  → TenantMiddleware resolve tenant
  → decode JWT
  → tenant do token == tenant do Host?
  → user ativo + cv bate + sid não revogado?
  → ResolveEffectiveAccess (roles + bundles + permission codes)
  → require_permission("iam.users.read") → AuthorizationService.check(...)
  → handler (RLS ativa na conexão lanstar_app)
```

### 4.3 Invalidação de credenciais

Qualquer uma destas ações incrementa `credentials_version` e apaga refreshes do usuário:

- Troca de senha
- Desativação
- Exclusão
- Atribuição / remoção / troca de roles

O access token antigo falha na próxima request mesmo antes de expirar.

---

## 5. Classificação: o Lanstar é um IAM?

**Sim, como IAM de aplicação.** Cobre identidade local, autenticação JWT, autorização RBAC/ACL/ABAC, isolamento multi-tenant e administração de usuários/papéis.

**Sim, como base de IAM plataforma.** Os dez blocos típicos de um IdP enterprise estão no código (ver seção 15) — o que falta é endurecimento operacional, não a capacidade:

1. Federação / SSO (OAuth2/OIDC inbound, SAML, Google/Azure AD)
2. MFA / 2FA (TOTP, WebAuthn)
3. Ciclo de vida completo (invite, reset, onboarding, offboarding)
4. Políticas avançadas (lockout, password history, expiração, conditional access)
5. Audit trail persistente e consultável
6. Identidades não-humanas (API keys, service accounts, client credentials)
7. Protocolos como **provedor** (OIDC/OAuth Authorization Server)
8. ABAC / policies contextuais
9. SCIM / sync com diretórios
10. Consent / scopes para apps terceiros

O roadmap da seção 7 é o histórico de como cada bloco entrou; a seção 15 diz onde cada um vive hoje.

---

## 6. Visão-alvo: Lanstar Identity Provider

**Decisão de arquitetura:** o Lanstar passa a ser um **Identity Provider multi-tenant**. Outras aplicações autenticam nele; ele também pode **federar** IdPs externos (Google, Microsoft Entra / Azure AD, SAML corporativo).

### 6.1 Diagrama-alvo

```
                    ┌──────────────┐  ┌──────────────┐  ┌─────────────┐
                    │ Lanstar SPA  │  │ Apps externas│  │ SCIM (Entra)│
                    └──────┬───────┘  └──────┬───────┘  └──────┬──────┘
                           │                 │                  │
                           ▼                 ▼                  ▼
                 ┌─────────────────────────────────────────────────────┐
                 │                 Lanstar IdP                         │
                 │  AuthN (senha/MFA/SSO)  │  OIDC/OAuth AS + Consent │
                 │  RBAC + ABAC            │  Service accounts / keys │
                 │  Users / Roles / SCIM   │  Audit store             │
                 └────────────────────────────┬────────────────────────┘
                                              │
                         ┌────────────────────┼────────────────────┐
                         ▼                    ▼                    ▼
                   PostgreSQL+RLS           Redis              IdPs externos
                                                              (OIDC / SAML)
```

### 6.2 Stack prevista (fixa)

| Capacidade | Tecnologia |
|------------|------------|
| OIDC/OAuth2 Authorization Server | Authlib |
| MFA TOTP | pyotp |
| MFA WebAuthn / passkeys | webauthn |
| ABAC | Casbin (adapter SQLAlchemy) |
| SCIM 2.0 | Rotas FastAPI `/scim/v2` |
| SAML SP | pysaml2 |
| Tokens para apps externas | JWT **RS256** + JWKS (issuer por tenant/Host) |
| Persistência | PostgreSQL + FORCE RLS |
| Sessões / rate limit | Redis (+ tabela `sessions`) |

---

## 7. Roadmap completo (fases)

Ordem por dependência: fundação → audit → lifecycle/políticas → MFA → OIDC+consent → identidades máquina → federação → ABAC → SCIM.

### Fase 0 — Fundação compartilhada

Objetivo: preparar o núcleo sem quebrar o contrato atual da SPA.

- Pacote/módulos alinhados a Clean Architecture, CommandBus e EventBus
- Claims JWT adicionais: `amr` / `acr` (método de autenticação), `sid` (session id)
- Tabela `sessions` (user, tenant, IP, user-agent, amr, expiração, revogação); refresh Redis referencia `session_id`
- Feature flags (`IAM_OIDC_ENABLED`, políticas de MFA por role, etc.)
- Novas permissões: `audit.read`, `sessions.revoke`, `oauth_clients.*`, `service_accounts.*`, `api_keys.*`, `federation.*`, `policies.*`, `scim.provision`

### Fase 1 — Audit trail persistente *(ponto 5)*

Hoje o audit só escreve em log. Um IAM sério guarda eventos **consultáveis**.

- Tabela `audit_events` (ator humano/serviço/sistema, ação, recurso, IP, payload JSONB, `tenant_id`) + RLS
- Trocar o sink de `audit_handlers.py` para persistência (manter log estruturado em paralelo)
- API `GET /api/v1/audit-events` + UI Admin/Platform
- Incluir logins falhos, grants de role, mudanças de política, etc.

### Fase 2 — Ciclo de vida + políticas avançadas *(pontos 3 e 4)*

**Lifecycle**

- Convites (`user_invitations`) → e-mail → aceite com definição de senha
- Forgot / reset password (substituir o placeholder da `LoginPage`)
- Onboarding: `must_change_password`, `invitation_accepted_at`
- Offboarding: desativar + `POST /users/{id}/revoke-sessions` + “sair de todos os dispositivos”

**Políticas por tenant (`tenant_auth_policies`)**

- Lockout após N tentativas (`login_attempts` / Redis)
- Histórico de senhas (`password_history`) e rejeição de reuso
- Expiração de senha (força reset no login)
- Conditional access v1: tenant inativo, allowlist de IP, MFA pendente
- Flags: `mfa_required`, `password_login_enabled`, idle de sessão

### Fase 3 — MFA / 2FA *(ponto 2)*

- Métodos: **TOTP** (authenticator) e **WebAuthn** (passkeys)
- Fluxo: senha OK → `mfa_token` de curta duração → `POST /auth/mfa/verify` → access+refresh com `amr`
- Recovery codes (hashes)
- UI de enroll, challenge no login e gestão de métodos
- Integração com policy do tenant e obrigatoriedade para roles sensíveis (ADMIN/PLATFORM)

### Fase 4 — OIDC/OAuth como provedor + consent/scopes *(pontos 7 e 10)*

Núcleo de “IAM de verdade”: o Lanstar **emite** tokens para outros clients.

- Grants: Authorization Code + PKCE, Refresh, Client Credentials
- Tabelas: `oauth_clients`, `oauth_scopes`, `oauth_authorization_codes`, `oauth_consents`
- Endpoints: `/.well-known/openid-configuration`, `/oauth/authorize`, `/oauth/token`, `/oauth/revoke`, `/oauth/introspect`, `/jwks.json`, `/userinfo`
- Tela de **consent**: “O app X solicita os escopos Y”
- Admin de clients OAuth
- Scopes padrão (`openid`, `profile`, `email`, `offline_access`) + scopes de API mapeados a permission codes
- **Issuer por tenant** coerente com o Host (`https://{tenant}.{base}/`)
- Assinatura **RS256** + JWKS para consumo externo

### Fase 5 — Identidades não-humanas *(ponto 6)*

- `service_accounts` (sem senha interativa; roles/permissões)
- `api_keys` (prefixo + hash, expiração, last_used; header `X-API-Key` ou Bearer)
- Client Credentials ligando client OAuth ↔ service account
- Audit com `actor_type=service`
- UI: criar conta de serviço / chave (secret exibido **uma vez**)

### Fase 6 — Federação / SSO inbound *(ponto 1)*

Login com IdP externo, conta ligada ao usuário local do tenant.

- `identity_providers` (tipo `oidc` | `saml`, metadata, client credentials, mapeamento de atributos)
- `federated_identities` (`user_id` + `external_subject`)
- OIDC: Google, Microsoft Entra / Azure AD (JIT provision opcional por policy)
- SAML 2.0 SP para IdPs corporativos
- Botões SSO na tela de login; admin configura IdPs por tenant

### Fase 7 — ABAC *(ponto 8)*

RBAC continua como base; Casbin avalia atributos e contexto.

- Após resolver permissões efetivas: `PolicyEnforcer.enforce(subject, action, resource, env)`
- Exemplos de env: IP, horário, ownership do recurso, rank da role alvo
- Migrar regras hoje hardcoded (ex.: hierarquia em `role_hierarchy.py`) para policies administráveis
- UI de policies (`policies.*`); decisões contextuais ficam no backend (o `can()` do frontend continua baseado em permission codes)

### Fase 8 — SCIM 2.0 *(ponto 9)*

Provisionamento a partir de diretórios (Entra, Okta, etc.).

- `/scim/v2/Users` e `/Groups` (create, replace, patch, delete, filter)
- Auth via Bearer de service account com `scim.provision`
- Group SCIM ↔ Role Lanstar; User SCIM ↔ User + roles
- Sempre escopado ao tenant do Host; documentação de mapeamento de atributos

---

## 8. Mapa dos 10 pontos → fases

| # | Capacidade | Fase |
|---|------------|------|
| 1 | Federação / SSO (OIDC, SAML, Google/Azure, IdP externo) | 6 |
| 2 | MFA / 2FA (TOTP, WebAuthn) | 3 |
| 3 | Ciclo de vida (invite, reset, onboarding, offboarding) | 2 |
| 4 | Políticas avançadas (lockout, history, expiração, conditional access) | 2 |
| 5 | Audit trail persistente | 1 |
| 6 | Identidades não-humanas (API keys, service accounts, M2M, client credentials) | 5 (+ grant na 4) |
| 7 | Provedor OIDC/OAuth (Lanstar é o IdP) | 4 |
| 8 | ABAC / policies finas | 7 |
| 9 | SCIM / sync | 8 |
| 10 | Consent / scopes OAuth | 4 |

---

## 9. Ordem sugerida de entrega (PRs)

1. Audit DB + API + UI  
2. Invitations + password reset + revoke sessions  
3. Tenant auth policies + lockout + password history  
4. MFA TOTP (+ recovery) → WebAuthn  
5. OIDC AS (RS256/JWKS) + clients + consent + scopes  
6. Service accounts + API keys + client_credentials  
7. Federation OIDC (Google/Azure) → SAML SP  
8. Casbin ABAC + migrar hierarchy guards  
9. SCIM Users/Groups  

Cada entrega deve incluir: migration Alembic, seed das permissões novas, testes (unit/integration + RLS), e atualização do README.

---

## 10. Frontend (visão transversal)

Novas áreas na SPA Quasar:

| Área | Uso |
|------|-----|
| Audit | Consulta de eventos |
| Sessions | Dispositivos / revogar |
| MFA | Enroll e gestão |
| OAuth clients | Apps que consomem o IdP |
| Service accounts / API keys | Integrações M2M |
| Identity providers | SSO por tenant |
| Policies | ABAC / auth policies |
| Invitations | Convites pendentes |
| Consent | Página OIDC first-party |
| Login | Reset, MFA challenge, botões SSO |

Permission codes novos devem ser espelhados em `frontend/src/constants/permissions.ts`.

---

## 11. Segurança e testes (diretrizes)

- Secrets e tokens: apenas **hashes** em banco/Redis; secrets de API key/client exibidos uma vez
- Rotação de chaves JWKS documentada
- Rate limits específicos para forgot-password, MFA verify e `/oauth/token`
- Sem client secrets em logs de audit (payload redigido)
- Seed demo bloqueado fora de `development` (comportamento atual)
- Suites mínimas por fase: OIDC (code+PKCE, client_credentials), MFA (enroll/verify/recovery), SCIM (filter/patch), RLS por tenant

---

## 12. Glossário rápido

| Termo | Significado |
|-------|-------------|
| **AuthN** | Autenticação — prova de identidade |
| **AuthZ** | Autorização — o que a identidade pode fazer |
| **RBAC** | Role-Based Access Control — permissões via papéis |
| **ABAC** | Attribute-Based Access Control — decisões por atributos/contexto |
| **IdP** | Identity Provider — quem autentica e emite identidade/tokens |
| **SP / RP** | Service Provider / Relying Party — app que confia no IdP |
| **OIDC** | OpenID Connect — identidade sobre OAuth2 |
| **SAML** | Federação XML clássica em ambientes enterprise |
| **SCIM** | Protocolo de provisionamento de usuários/grupos |
| **MFA / AMR** | Multi-factor; `amr` = Authentication Method Reference no token |
| **PKCE** | Extensão OAuth para clients públicos (SPA/mobile) |
| **RLS** | Row Level Security no PostgreSQL |
| **JIT** | Just-in-Time provisioning na primeira autenticação federada |
| **Consent** | Usuário autoriza um client a receber certos scopes |
| **M2M** | Machine-to-machine — client credentials / API keys |

---

## 13. Referências no código (estado atual)

| Tema | Caminhos principais |
|------|---------------------|
| Login / refresh / logout | `backend/src/modules/authentication/` |
| JWT claims / token service | `.../value_objects/access_token_claims.py`, `.../services/jwt_token_service.py` |
| Refresh Redis / denylist de sessão | `.../services/redis_refresh_token_store.py`, `shared/.../security/session_denylist.py` |
| Engine de autorização | `backend/src/shared/infrastructure/security/authorization.py` (+ `authorization_adapters.py`) |
| `require_permission` | `backend/src/shared/infrastructure/security/dependencies.py` |
| Códigos de permissão e bundles | `.../permission_codes.py`, `backend/src/modules/permissions/groups/` |
| ACL por recurso | `backend/src/modules/iam/acl/service.py` |
| Hierarquia de roles | `HierarchyPolicy` em `.../authorization.py` (ranks em `.../role_hierarchy.py`) |
| Tenant / Host | `.../tenant_middleware.py`, `.../tenant_host.py` |
| Audit persistente | `backend/src/modules/iam/audit/service.py`, `shared/.../audit_handlers.py` |
| Catálogo de serviços / entitlements / quotas | `backend/src/modules/services/` |
| Medição de uso | `backend/src/modules/services/usage.py`, `usage_routes.py` |
| Navegação (menu no backend) | `backend/src/modules/navigation/` |
| Users / Roles / Permissions | `backend/src/modules/{users,roles,permissions}/` |
| Frontend auth | `frontend/src/stores/auth.ts`, `composables/usePermissions.ts` |
| Frontend por serviço | `frontend/src/modules/{iam,platform,integration}/` |
| Visão geral do produto | `README.md` |

---

## 14. Conclusão

O Lanstar evoluiu de IAM de aplicação (RBAC multi-tenant) para uma **base de Identity Provider**: audit durável, lifecycle, políticas, MFA, OIDC/OAuth com consent, identidades máquina, federação SSO, ABAC e SCIM estão no código (ver seção 15).

Continue endurecendo cada capacidade (SMTP real, WebAuthn com verificação criptográfica completa, exchange OIDC outbound com httpx, Casbin sync, cobertura de contrato SCIM) conforme a necessidade de produção.

---

## 15. Status de implementação (código)

As fases do roadmap foram introduzidas no repositório:

| Fase | Entrega principal | Onde |
|------|-------------------|------|
| 0 | Claims `amr`/`acr`/`sid`, `auth_sessions`, flags IAM, permissões | `access_token_claims`, migration `0011`, `permission_codes`, settings |
| 1 | Audit persistente + API | `audit_events`, `AuditService`, `GET /api/v1/audit-events`, UI Audit |
| 2 | Convites, reset de senha, políticas, lockout, histórico | `lifecycle`, `policies`, rotas `/auth/forgot-password`, `/invitations` |
| 3 | MFA TOTP + WebAuthn + recovery | `mfa`, `/auth/mfa/*`, UI MFA |
| 4 | OIDC AS + consent/scopes + JWKS | `oauth`, `/.well-known/openid-configuration`, `/oauth/*` |
| 5 | Service accounts + API keys + client_credentials | `machine`, `/service-accounts`, `/api-keys` |
| 6 | Federação OIDC/SAML SP | `federation`, `/identity-providers`, `/auth/sso/*` |
| 7 | ABAC | `abac.PolicyEnforcer`, `/access-policies` |
| 8 | SCIM 2.0 Users/Groups | `/api/v1/scim/v2/*` |

Migration: `backend/alembic/versions/0011_iam_platform.py`. Aplicar com `alembic upgrade head` e re-seed para novas permissões.

Sobre o Hub (evolução posterior ao roadmap acima): ACL (`0014`), namespaces e bundles (`0015`), catálogo de serviços (`0016`/`0018`) e medição de uso (`0017`). Documentos: [AUTHORIZATION.md](AUTHORIZATION.md), [ACL.md](ACL.md), [SERVICE_HUB.md](SERVICE_HUB.md), [SECURITY.md](SECURITY.md).
