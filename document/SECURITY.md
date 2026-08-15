# Vizion — Segurança (estado do código)

O que o Hub garante hoje, onde está configurado e o que é decisão consciente de operação. Autorização tem documento próprio ([AUTHORIZATION.md](AUTHORIZATION.md), [ACL.md](ACL.md)); aqui está o resto: tokens, sessões, cabeçalhos, isolamento, segredos, auditoria e supply chain.

---

## 1. Autenticação e tokens

| Peça | Comportamento | Onde |
|------|---------------|------|
| Access token | JWT **HS256**, TTL 15 min (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`), enviado em `Authorization: Bearer` | [jwt_token_service.py](../backend/src/modules/authentication/services/jwt_token_service.py) |
| Claims | `sub`, `tenant_id`, `tenant_slug`, `cv`, `sid`, `amr`, `acr`, `iat`, `exp` — **sem** e-mail, nome ou roles | [access_token_claims.py](../backend/src/modules/authentication/value_objects/access_token_claims.py) |
| Identidade / permissões | `GET /api/v1/auth/me` (roles, permissões, serviços contratados) | [auth_routes.py](../backend/src/modules/authentication/routes/auth_routes.py) |
| Refresh token | Opaco, guardado no Redis apenas como SHA-256, TTL 7 dias, rotação a cada uso | [redis_refresh_token_store.py](../backend/src/modules/authentication/services/redis_refresh_token_store.py) |
| Cookie de refresh | `httpOnly`, `SameSite=lax`, `Secure` fora de development, prefixo **`__Host-`** em produção (sem `Domain`, `Path=/`) | [auth_cookies.py](../backend/src/modules/authentication/routes/auth_cookies.py) |
| Access no frontend | Só em memória — nunca `localStorage`/`sessionStorage` | [stores/auth.ts](../frontend/src/stores/auth.ts) |

O JWT enxuto não é estética: cada claim de perfil é dado que vaza em log, proxy e histórico do browser, e que fica **velho** dentro de um token válido por 15 minutos.

### Revogação imediata

Dois mecanismos, complementares:

- **`cv` (credentials_version)** — troca de senha, desativação, exclusão ou mudança de roles incrementa o contador e apaga os refresh do usuário. Access antigo falha na próxima request.
- **Denylist de sessão** — `revoked_session:{sid}` no Redis, TTL = vida do access + 60s de folga. Logout e revogação de sessão gravam a chave; `get_current_user` recusa o `sid`. Sem isso, revogar sessão só matava o refresh e o access continuava válido por até 15 min ([session_denylist.py](../backend/src/shared/infrastructure/security/session_denylist.py)).

### MFA e senhas

TOTP e WebAuthn implementados, obrigatórios para as roles em `IAM_MFA_REQUIRED_ROLES` (default `ADMIN,PLATFORM`). Senhas com bcrypt via port `PasswordHasher` — a troca por Argon2id é localizada nessa porta e está aprovada como evolução, não como pré-requisito.

---

## 2. Cabeçalhos HTTP

[`SecurityHeadersMiddleware`](../backend/src/shared/infrastructure/security/security_headers_middleware.py) aplica em toda resposta:

| Header | Valor |
|--------|-------|
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'` (política relaxada só em `/docs`, `/redoc`, `/openapi.json`) |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |
| `Permissions-Policy` | `geolocation=(), camera=(), microphone=(), payment=()` |
| `Cross-Origin-Opener-Policy` / `Cross-Origin-Resource-Policy` | `same-origin` |
| `X-Permitted-Cross-Domain-Policies` | `none` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` — ativo fora de development (`HSTS_ENABLED`) |
| `Cache-Control` | `no-store` quando a request traz `Authorization` ou cookie |

A API responde JSON, por isso a CSP nega tudo por padrão. A CSP da SPA é responsabilidade do nginx que serve o bundle.

---

## 3. Isolamento multi-tenant

Quatro camadas independentes, na ordem em que atuam:

1. **Host** → tenant. O primeiro label do Host resolve o slug; `ALLOWED_TENANT_BASE_DOMAINS` restringe os sufixos aceitos (obrigatório fora de development).
2. **Token vs Host.** JWT de outro tenant é rejeitado mesmo com assinatura válida.
3. **Engine.** Estágio `TENANT` é hard-fail e não é sobreponível por ACL/ABAC.
4. **RLS.** `FORCE ROW LEVEL SECURITY` em toda tabela tenant-scoped; a API conecta como `vizion_app`, que **não** tem `BYPASSRLS`. Migrations/seed usam `vizion` / `vizion_migrate`.

O bypass explícito (`bind_rls_bypass`) existe para leitura cross-tenant da plataforma (`usage.read_all`, catálogo de serviços) e para scripts operacionais. É pontual, sempre em `try/finally`, e cada uso passa por permissão platform-only.

Verificação: [test_rls_policies.py](../backend/tests/integration/test_rls_policies.py) conecta como `vizion_app` e prova que tenant A não lê nem escreve dados de B; [test_tenant_isolation.py](../backend/tests/integration/test_tenant_isolation.py) cobre o caminho HTTP.

---

## 4. Rate limiting e quotas

| Camada | Regra |
|--------|-------|
| API geral | `RATE_LIMIT_REQUESTS` por janela, chave `tenant:IP` |
| `/auth/*` | limite menor (`AUTH_RATE_LIMIT_REQUESTS`) — login, refresh, forgot-password, MFA |
| Por serviço | `ServiceQuotaGuard` aplica `requests_per_minute` de `tenant_services.quotas` e mede o consumo |

O IP vem de `X-Real-IP`/`X-Forwarded-For` — **confie nisso somente atrás de um proxy que sobrescreva o header**. WAF/rate limit de borda continua recomendado e não é substituído por isto.

---

## 5. Segredos

- Configuração por variáveis de ambiente ([.env.example](../backend/.env.example)); `Settings` **recusa subir** fora de development com `JWT_SECRET_KEY` fraco (<32 chars ou valor de exemplo), sem `ALLOWED_TENANT_BASE_DOMAINS` ou com senha default de banco.
- Segredos de integração cifrados com Fernet (`INTEGRATION_SECRETS_KEY`); nunca retornados pela API.
- Refresh tokens, API keys e recovery codes só existem em banco/Redis como hash. Secret de client OAuth e API key aparecem **uma vez** na criação.
- Vault/KMS e rotação automatizada são evolução documentada, não implementada. Rotação hoje: variável de ambiente + restart (JWT) e re-emissão (chaves OIDC).

---

## 6. Auditoria

- `audit_events` (tenant-scoped, RLS) com ator, ação, recurso, IP, user-agent, payload JSONB e **`request_id`**.
- `request_id` vem do header `X-Request-ID` (ou é gerado) por [RequestIdMiddleware](../backend/src/shared/infrastructure/request_id_middleware.py), fica em `ContextVar` e é devolvido na resposta — um incidente se reconstrói ligando log ↔ audit pelo mesmo id.
- Negativas de autorização entram como `AUTHZ_DENIED` com estágio e motivo, sem secrets.
- Retenção: `AUDIT_RETENTION_DAYS` (default 365) aplicado por `python -m scripts.prune_audit`, que chama a função SQL `prune_audit_events`. Agende no cron/systemd do ambiente.

---

## 7. Supply chain e análise estática

```bash
cd backend
python -m pytest --cov=src            # cobertura
python -m bandit -c pyproject.toml -r src
pip-audit
```

Estado atual:

- **bandit**: sem findings de severidade alta. Restam Low/Medium conhecidos e revisados:
  - `B608` em [database_provider.py](../backend/src/modules/integrations/providers/database_provider.py) — a query é montada com identificadores validados por regex e `LIMIT` parametrizado, e o SQL customizado é obrigado a começar com `SELECT`/`WITH`, sem múltiplos statements e sem palavra-chave de escrita. É a natureza do provider (executar o SELECT configurado), não injeção.
  - `B105` em [oauth2_provider.py](../backend/src/modules/integrations/providers/oauth2_provider.py) — comparação com a string `"bearer"`, não senha.
  - `B507` em [sftp_provider.py](../backend/src/modules/integrations/providers/sftp_provider.py) — `AutoAddPolicy` só é usado quando há fingerprint esperado (verificado logo após o handshake) ou quando o operador pediu confiança na primeira conexão. O default é `RejectPolicy` + `known_hosts`.
- **pip-audit**: dependências da aplicação sem vulnerabilidade conhecida; o `pip` do venv de desenvolvimento é o único pacote com CVE aberto (ferramenta, não runtime) — atualize o venv ao recriá-lo.
- XML de resposta SOAP é parseado com `defusedxml` (sem DTD, sem entidade externa, sem expansão) — [soap_provider.py](../backend/src/modules/integrations/providers/soap_provider.py).

Fora do escopo do código, para o pipeline/deploy: semgrep, `npm audit`, Trivy nas imagens, TLS interno para Postgres/Redis, containers non-root com FS read-only, WAF de borda e alertas sobre `audit_events` (rajada de login falho, `AUTHZ_DENIED`).

---

## 8. Decisões conscientes

| Decisão | Racional |
|---------|----------|
| Access HS256 no monolito | Um único emissor e um único consumidor (a SPA). RS256/JWKS já existe e é usado onde faz diferença: o Authorization Server OIDC, cujos tokens saem para terceiros. Migrar o access só quando houver mais de um consumidor. |
| bcrypt hoje, Argon2id como evolução | A troca é localizada na port `PasswordHasher`; bcrypt com custo adequado é aceitável e não é o elo fraco. |
| ABAC só nega na v1 | Policy que concede sozinha transforma erro de configuração em escalonamento de privilégio. |
| Entitlement abstém em falha de leitura | Indisponibilidade do catálogo não pode trancar todos os tenants fora do Hub; o RBAC continua barrando. |
| Seed de demonstração | Bloqueado fora de `development` a menos que `SEED_ALLOW_INSECURE=true`. |
