*Lanstar — resumo da semana*

*Período de trabalho*: 10 a 14 de agosto de 2026 (segunda a sexta).

A semana passada o template já autenticava e controlava permissões (RBAC). Esta semana o produto virou plataforma: **multi-tenant**, **IAM completo** e **hub de integrações**.

O que ficou pronto:

*Multi-tenancy*
• Isolamento por tenant no PostgreSQL (Row Level Security)
• Acesso pelo subdomínio do Host (sem seletor de tenant no login)
• Dois tenants de seed: `universe` (produto) e `bigbang` (operações / PLATFORM)
• API e tela de administração de tenants (criar, ativar, desativar, administrador do tenant)
• Postgres e Redis só em localhost (não expostos na internet)

*Segurança*
• Cookie HttpOnly para refresh (token de acesso só em memória, sem localStorage)
• JWT com PyJWT; sessão invalidada ao trocar senha, desativar usuário ou mudar roles
• Hierarquia de papéis: ninguém gerencia par ou superior (PLATFORM > ADMIN > MANAGER > …)
• Rate limit por tenant + IP; cookie Secure configurável

*IAM (Identity and Access Management)*
• Audit consultável, convites, reset de senha, políticas (lockout, histórico)
• MFA (TOTP / WebAuthn), OAuth/OIDC (Lanstar como provedor), consent e JWKS
• Contas de serviço e API keys (identidades máquina)
• Federação SSO (OIDC/SAML), ABAC e SCIM 2.0
• Telas: Audit, MFA, OAuth clients, Machine identities, Federation
• Diálogo de atribuição de permissões nas roles

*Integrações (Integration Hub)*
• Página + camada desacoplada (Page → Service → Layer → Provider)
• API FastAPI; secrets cifrados no backend (nunca no browser)
• Providers: REST, OAuth2, mTLS, Webhook, SFTP, arquivo HTTPS, SOAP, sync incremental, Database (somente leitura)
• Área restrita ao PLATFORM (`galileu` no tenant `bigbang`)

*Documentação*
• Playbook HOWTODO (AuthZ multi-tenant / platform-only)
• `document/0002-sistema-iam.md`
• `document/0003-integration-layer.md`

*Acesso*

Produto (tenant universe):
http://universe.134.209.122.250:9000

Plataforma (tenant bigbang):
http://bigbang.134.209.122.250:9000

(DNS / hosts: `universe.lanstar.com.br`, `bigbang.lanstar.com.br`, `universe.lanstar.local`, `bigbang.lanstar.local`)

Não use o IP sem subdomínio — a API exige o slug no Host.

*Contas para testar* (senha igual em todas: 123Mudar.)

Tenant **universe** (produto):

1) Usuário: admin
   Perfil: ADMIN (administração)

2) Usuário: manager
   Perfil: MANAGER (gestor)

3) Usuário: operator
   Perfil: OPERATOR (operador)

4) Usuário: user
   Perfil: CLIENT (cliente)

5) Usuário: viewer
   Perfil: VIEWER (somente leitura)

Tenant **bigbang** (plataforma / IAM / integrações / tenants):

6) Usuário: galileu
   Perfil: PLATFORM
