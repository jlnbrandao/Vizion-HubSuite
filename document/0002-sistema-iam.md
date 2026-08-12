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
| Cookie | `lanstar_refresh_token`, **httpOnly**, `SameSite=lax`, `Secure` fora de development |
| Frontend | Access token **somente em memória** (não vai para `localStorage`) |
| Logout | Invalida o refresh; access expira naturalmente ou falha por `cv` |
| Invalidação forte | Campo `credentials_version` (`cv` no JWT): sobe em troca de senha, desativação, delete ou mudança de roles — access antigo é rejeitado e refreshes do usuário são apagados |

**Claims principais do access token:** `sub`, `email`, `full_name`, `tenant_id`, `tenant_slug`, `role_ids`, `cv`, `iat`, `exp`.

**Endpoints:** `POST /api/v1/auth/login`, `/refresh`, `/logout`.

### 3.2 Autorização (AuthZ) — RBAC

Modelo clássico:

```
Permission (resource.action)
        ↑
   Role ⇄ Permissions
        ↑
   User ⇄ Roles
```

- Códigos canônicos em `backend/src/shared/infrastructure/security/permission_codes.py` (espelhados no frontend).
- Backend: `Depends(require_permission(...))` — valida JWT, tenant do Host, usuário ativo, `cv`, e permissões efetivas.
- Frontend: `can()` / `canAny()` / `meta.permissions` nas rotas (espelho de UX; a barreira real é o backend).
- **Hierarquia de roles:** `PLATFORM` > `ADMIN` > `MANAGER` > `OPERATOR` > `CLIENT` > `VIEWER`. Quem gerencia usuários/roles **não** pode gerenciar pares ou superiores.
- Permissões **platform-only** (`tenants.*`, `system.settings`, `dashboard.platform`) existem só no tenant de operações (`bigbang`), não no RBAC comum de produto.

### 3.3 Multi-tenancy e isolamento

| Elemento | Detalhe |
|----------|---------|
| Tabela `tenants` | Isolamento lógico; seed cria `universe` (app) e `bigbang` (ops) |
| Resolução | Primeiro label do Host → slug → tenant (`universe.localhost`, `bigbang.lanstar.com.br`, …) |
| RLS | `FORCE ROW LEVEL SECURITY` em users, roles, permissions e associações |
| Defense-in-depth | Repositórios SQLAlchemy também filtram por `tenant_id` |
| Roles de banco | `lanstar` (migrate/owner), `lanstar_app` (API, sujeita a RLS), `lanstar_migrate` (opcional, `BYPASSRLS`) |

### 3.4 Sessões e rate limiting

- Refresh recarrega `role_ids` / `is_active` do banco a cada renovação.
- Rate limit Redis por `tenant:IP` (`X-Real-IP`); login/refresh com limite mais baixo que a API geral.
- Eventos de domínio (login, logout, CRUD de users/roles/permissions) alimentam um **audit em stdout** (`lanstar.audit`) — ainda **não** consultável via API.

### 3.5 Ciclo de vida parcial

Já existe:

- CRUD de usuários, roles e permissões
- Troca de senha (com `current_password` quando for a própria)
- Ativar / desativar usuário (com invalidação de sessão)
- Provisionamento de tenant + admin (`bigbang`)

Ainda **não** existe (placeholder ou ausente):

- Convite por e-mail
- Forgot / reset password (UI mostra “contact admin”)
- MFA
- SSO / federação
- Audit consultável
- OAuth como provedor para apps externas

### 3.6 Catálogo de permissões (atual)

| Recurso | Códigos |
|---------|---------|
| users | `create`, `read`, `update`, `delete`, `assign` |
| roles | `create`, `read`, `update`, `delete`, `assign` |
| permissions | `create`, `read`, `update`, `delete` |
| dashboard | `admin`, `manager`, `operator`, `client`, `viewer`, `platform` |
| system | `settings` (platform) |
| tenants | `create`, `read`, `update`, `activate`, `deactivate` (platform) |

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
  → TenantMiddleware resolve tenant
  → decode JWT
  → tenant do token == tenant do Host?
  → user ativo + cv bate?
  → ResolveEffectiveAccess (roles + permission codes)
  → require_permission("users.read") ?
  → handler
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

**Sim, como IAM de aplicação.** Cobre identidade local, autenticação JWT, autorização RBAC, isolamento multi-tenant e administração de usuários/papéis.

**Ainda não, como IAM plataforma.** Faltam os blocos típicos de um IdP enterprise:

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

Os dez pontos acima são exatamente o escopo do roadmap da seção 7.

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
| Refresh Redis | `.../services/redis_refresh_token_store.py` |
| `require_permission` | `backend/src/shared/infrastructure/security/dependencies.py` |
| Códigos de permissão | `.../permission_codes.py` |
| Hierarquia de roles | `.../role_hierarchy.py` |
| Tenant / Host | `.../tenant_middleware.py`, `.../tenant_host.py` |
| Audit (stdout) | `backend/src/shared/infrastructure/audit_handlers.py` |
| Users / Roles / Permissions | `backend/src/modules/{users,roles,permissions}/` |
| Frontend auth | `frontend/src/stores/auth.ts`, `composables/usePermissions.ts` |
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
