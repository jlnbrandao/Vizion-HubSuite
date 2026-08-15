# Vizion — Integration Layer (Integration Hub)

Documento de referência da área de **Integrações** do **enterprise-template** (produto Vizion): arquitetura desacoplada (Page → Components → Service → Layer → Provider), estado atual da **ETAPA 1**, regras de segurança/RBAC/multi-tenancy e roadmap até o Integration Hub completo.

| | |
|---|---|
| **Produto** | Vizion — Enterprise Template |
| **Escopo** | Hub de integração com sistemas terceiros (REST, OAuth2, mTLS, Webhook, SFTP, SOAP, sync incremental, DB, …) |
| **Stack (alvo)** | Vue 3 / Quasar (UI) · FastAPI (orquestração) · Secret Manager · Providers por protocolo |
| **Status atual** | **ETAPA 4** — API + REST + OAuth2 + mTLS; demais providers ainda stub |
| **Alvo** | Integration Hub multi-tenant, extensível, sem secrets no browser |

---

## 1. Objetivo

Permitir que um tenant (hoje: operações **PLATFORM** / `ows`) configure, teste e sincronize integrações com sistemas externos **sem** acoplar a UI aos protocolos e **sem** o browser falar diretamente com o terceiro.

Princípios:

1. **Page** só compõe tela e orquestra UX.
2. **Components** são apresentação reutilizável.
3. **IntegrationService** é a fachada de operações (CRUD, test, sync, logs).
4. **IntegrationLayer** seleciona o **Provider** (Strategy).
5. **Provider** encapsula o método/protocolo.
6. **FastAPI** (a partir da ETAPA 2) é o único ponto que fala com o servidor terceiro e com o Secret Manager.
7. Novos protocolos (MQTT, Kafka, GraphQL, gRPC, EDI, …) entram como novos providers — **sem reescrever** `IntegrationPage.vue`.

---

## 2. Fluxo de responsabilidade

```text
Usuário
   ↓
IntegrationPage.vue          (composição / RBAC visual)
   ↓
components/integrations/*    (cards, tabela, form dinâmico, status, logs)
   ↓
IntegrationService           (operações: list/create/update/delete/test/sync/logs)
   ↓
IntegrationLayer             (resolve provider por type)
   ↓
Provider (REST, OAuth2, …)   (protocolo)
   ↓
Backend FastAPI              (ETAPA 2+ — ainda não na ETAPA 1)
   ↓
Secret Manager + Servidor terceiro
```

**Regra fundamental:** o frontend Vue **nunca** abre conexão HTTP/SFTP/SOAP/mTLS diretamente com o sistema terceiro. Na ETAPA 1 os providers retornam **mock**; a partir da ETAPA 2 as operações reais passam pelo FastAPI.

---

## 3. Estrutura de pastas (implementada)

```text
frontend/src/
├── pages/
│   └── IntegrationPage.vue
├── components/integrations/
│   ├── IntegrationMethodCard.vue
│   ├── IntegrationMethodTable.vue
│   ├── IntegrationForm.vue          # formulário dinâmico por método
│   ├── IntegrationStatus.vue
│   ├── IntegrationTestResult.vue
│   ├── IntegrationSyncStatus.vue
│   └── IntegrationLogs.vue
└── layers/integration/
    ├── index.ts
    ├── IntegrationLayer.ts
    ├── IntegrationService.ts
    ├── models/
    │   └── Integration.ts
    ├── types/
    │   └── IntegrationTypes.ts
    ├── mock/
    │   └── mockIntegrations.ts
    └── providers/
        ├── IntegrationProvider.ts   # interface + BaseIntegrationProvider
        ├── RestProvider.ts
        ├── OAuth2Provider.ts
        ├── MTLSProvider.ts
        ├── WebhookProvider.ts
        ├── SFTPProvider.ts
        ├── HttpFileProvider.ts
        ├── SoapProvider.ts
        ├── IncrementalSyncProvider.ts
        └── DatabaseProvider.ts
```

Convenção do projeto: a “camada” vive em `frontend/src/layers/integration/` (não existia `layers/` antes). O backend espelhará Router → Service → Layer → Provider nas etapas seguintes.

---

## 4. Provider Pattern (Strategy)

Contrato:

```typescript
interface IntegrationProvider {
  readonly type: string
  testConnection(integration: Integration): Promise<IntegrationTestResult>
  fetch(integration: Integration): Promise<unknown>
  sync(integration: Integration): Promise<IntegrationSyncResult>
}
```

A `IntegrationLayer` registra os providers e resolve por `integration.type`:

```text
IntegrationLayer
       │
       ├── rest ──────────────► RestProvider
       ├── oauth2 ────────────► OAuth2Provider
       ├── mtls ──────────────► MTLSProvider
       ├── webhook ───────────► WebhookProvider
       ├── sftp ──────────────► SFTPProvider
       ├── http_file ─────────► HttpFileProvider
       ├── soap ──────────────► SoapProvider
       ├── incremental_sync ──► IncrementalSyncProvider
       └── database ──────────► DatabaseProvider
```

A Page **não** importa providers concretos — só o `IntegrationService` / abstrações exportadas por `layers/integration`.

---

## 5. Modelo de domínio

Entidade conceitual `Integration`:

| Campo | Descrição |
|-------|-----------|
| `id` | Identificador |
| `tenantId` | Tenant dono (nunca confiar só no valor enviado pelo browser) |
| `name` / `description` | Metadados de UX |
| `type` | Método (`rest`, `oauth2`, …) |
| `status` | Ver §6 |
| `configuration` | Config **não sensível** tipada por método |
| `createdAt` / `updatedAt` | Auditoria |
| `lastSyncAt` | Última sincronização |
| `lastError` | Último erro seguro (sem secrets) |

### 5.1 Configurações por método (frontend)

Cada tipo tem interface própria (`RestConfig`, `OAuth2Config`, …). Campos sensíveis **não** são persistidos no estado da UI além de flags como `secretsConfigured: boolean`.

| Método | Exemplos de campos não sensíveis |
|--------|----------------------------------|
| REST | `baseUrl`, `endpoint`, `httpMethod`, `authType`, `timeoutMs`, `pagination` |
| OAuth2 | `tokenUrl`, `clientId`, `scope`, `grantType`, `endpoint` |
| mTLS | `baseUrl`, `endpoint` |
| Webhook | `eventTypes`, `signatureHeader` |
| SFTP | `host`, `port`, `username`, `remotePath`, `filenamePattern`, `encoding`, `delimiter`, `scheduleCron` |
| HTTPS file | `url`, `format`, `encoding`, `delimiter`, `authType`, `timeoutMs` |
| SOAP | `wsdlUrl`, `operation`, `soapAction`, `endpoint`, `namespace`, `authType`, `timeoutMs` |
| Incremental | `baseUrl`, `endpoint`, `cursorField`, `cursorValue`, `pageSize`, `authType` |
| Database | `host`, `port`, `database`, `username`, `schema`, `table`, `query`, `rowLimit`, `readOnly: true` |

### 5.2 O que **não** armazenar em texto puro / no browser

- `client_secret`, `private_key`, senhas, API keys, tokens de acesso  
- Qualquer segredo em `localStorage` / código Vue  

Destino: **Backend / Secret Manager** (ETAPA 2+).

---

## 6. Status

| Código | UI |
|--------|-----|
| `ACTIVE` | Ativa |
| `INACTIVE` | Inativa |
| `ERROR` | Erro |
| `TESTING` | Testando |
| `SYNCING` | Sincronizando |
| `NEVER_SYNCED` | Nunca sincronizada |

Apresentação via `IntegrationStatus.vue` (`QBadge` / chip).

---

## 7. Métodos e orientação arquitetural

### 7.1 Tabela comparativa (indicativa)

| Método | Complexidade | Impacto no terceiro | Segurança | Orientação |
|--------|--------------|---------------------|-----------|------------|
| API REST | Baixa | Baixo | Alta | **Recomendado** |
| API REST + OAuth 2.0 | Média | Baixo | Muito alta | **Recomendado** |
| API + mTLS | Média/Alta | Muito baixo | Muito alta | **Recomendado** |
| Webhook | Média | Muito baixo | Muito alta | **Recomendado** |
| SFTP / CSV | Baixa | Muito baixo | Alta | Alternativa |
| HTTPS / JSON / CSV | Baixa | Muito baixo | Alta | Alternativa |
| SOAP | Média | Baixo | Alta | Alternativa |
| Sincronização incremental | Média | Muito baixo | Alta | **Recomendado** |
| Replicação / acesso DB | Alta | Médio/Alto | Média | **Não recomendado** como 1ª opção |

Constantes em `METHOD_COMPARISON` (`IntegrationTypes.ts`).

### 7.2 Aviso para banco de dados

> Acesso direto ao banco de dados do terceiro aumenta o acoplamento e pode gerar impacto operacional. Prefira API, Webhook, SFTP ou sincronização incremental sempre que possível.

Na UI: banner no formulário e na seção “Não recomendado”. Provider DB é **somente leitura** (`readOnly: true`).

---

## 8. UI (ETAPA 1)

Rota: `/integrations` · nome: `integrations` · página: `IntegrationPage.vue`.

A página apresenta:

- Lista de integrações (mock) com ações condicionadas a RBAC  
- Cards por tier (Recomendado / Alternativa / Não recomendado)  
- Tabela comparativa  
- Painel de status / sync, resultado de teste e logs  
- Dialog de criação/edição com **formulário dinâmico** por método (`IntegrationForm.vue`)

Não contém implementação de OAuth, HTTP client, SFTP, SOAP, retry, rate limit, parsing CSV, etc.

### 8.1 Menu

Item **Integrações** vem do dashboard PLATFORM (`PlatformDashboardProvider` → `route: /integrations`).  
Não duplicar o mesmo item em `useLayoutConfig` (evita dois entries na sidebar).

---

## 9. RBAC

### 9.1 Códigos

| Código | Uso |
|--------|-----|
| `integration.read` | Ver página / listar |
| `integration.create` | Criar |
| `integration.update` | Editar |
| `integration.delete` | Excluir |
| `integration.test` | Testar conexão |
| `integration.sync` | Sincronizar |
| `integration.read_logs` | Ver logs |

> Nota: o VO de permissão exige o formato `resource.action` (um ponto). Por isso o código de logs é `integration.read_logs`, **não** `integration.logs.read`.

### 9.2 Escopo PLATFORM

Esses códigos são **platform-only** (`PermissionCode.platform_only_codes()`):

- Existem no tenant de ops **`ows`**
- Entram no role **PLATFORM** (seed: usuário `root`)
- **Não** entram no RBAC de produto (`universe` / ADMIN)

Frontend: `PermissionCode.INTEGRATION_*` em `frontend/src/constants/permissions.ts`.  
Backend: catálogo + `admin_role_codes` **sem** integration; `platform_only_codes` **com** integration.

### 9.3 Barreiras

| Camada | Comportamento |
|--------|----------------|
| Rota Vue | `meta.permissions: [integration.read]` |
| UI | `v-if="can(...)"` nas ações |
| Backend (ETAPA 2+) | `Depends(require_permission(...))` — **obrigatório**; não confiar só no frontend |

---

## 10. Multi-tenancy

```text
Tenant
   └── Integration
          └── External System
```

- Cada integração pertence a um `tenant_id`.
- O backend (ETAPA 2+) determina o tenant pelo **contexto autenticado / Host**, não pelo payload do frontend.
- Usuário de um tenant não acessa integrações de outro.

Acesso UI demo: `http://ows.localhost:9000/integrations` como `root`.

---

## 11. Segurança

| Regra | Detalhe |
|-------|---------|
| Sem secrets no Vue | Client secret / keys / senhas não ficam no bundle nem em `localStorage` |
| Sem chamada direta ao terceiro | Browser → FastAPI → Provider → terceiro |
| Erros seguros | Mensagens de teste/sync não ecoam credenciais |
| Flag `secretsConfigured` | Indica presença de segredo no backend sem materializar o valor |
| Formulário | Campos de secret são toggles / referências, não inputs persistidos |

Fluxo alvo:

```text
IntegrationPage
      ↓
FastAPI
      ↓
Integration Service (backend)
      ↓
Secret Manager
      ↓
External Provider
```

---

## 12. Operações (fachada)

`IntegrationService` (frontend) — ETAPA 1 com armazenamento **in-memory** + mock:

| Operação | Comportamento atual |
|----------|---------------------|
| `list` / `getById` | Mock seed |
| `create` / `update` / `remove` | Mutação local |
| `test` | Provider stub → `IntegrationTestResult` |
| `sync` | Provider stub → `IntegrationSyncResult` (full/incremental) |
| `getLogs` | Log entries mock + append em test/sync |

Resultado de teste (UX):

- Sucesso: servidor, tempo (ms), autenticação, permissão/escopo  
- Falha: mensagem genérica sem secrets  

---

## 13. API FastAPI (alvo — ainda não implementada)

Prefixo planejado: `/api/v1/integrations`

```http
GET    /integrations
GET    /integrations/{id}
POST   /integrations
PUT    /integrations/{id}
DELETE /integrations/{id}

POST   /integrations/{id}/test
POST   /integrations/{id}/sync

GET    /integrations/{id}/status
GET    /integrations/{id}/logs
```

Separação:

```text
Router → Service → Integration Layer → Provider
```

Routers **não** implementam protocolos inline.

---

## 14. Roadmap por etapas

| Etapa | Escopo | Status |
|------:|--------|--------|
| **1** | Architecture + UI + mock + RBAC visual + providers stub | **Concluída** |
| **2** | `RestProvider` real (GET, headers, auth, timeout, paginação, rate limit, retry, test) + API FastAPI | **Concluída** |
| **3** | `OAuth2Provider` (Client Credentials; tokens só no backend) | **Concluída** |
| **4** | `MTLSProvider` (cert/key/CA no backend) | **Concluída** |
| **5** | `WebhookProvider` (assinatura, retry, idempotência, eventos address.*) | **Concluída** |
| **6** | `SFTPProvider` (CSV, encoding, schedule) | **Concluída** |
| **7** | `HttpFileProvider` (HTTPS JSON/CSV) | **Concluída** |
| **8** | `SoapProvider` | **Concluída** |
| **9** | `IncrementalSyncProvider` (`updated_since` / cursor) | **Concluída** |
| **10** | `DatabaseProvider` read-only + avisos fortes | **Concluída** |

**Regra de execução:** concluir → validar (lint/test/build) → **parar e aguardar aprovação** → próxima etapa.

Extensões futuras sem alterar a Page: MQTT, Kafka, AMQP, GraphQL, gRPC, EDI.

---

## 15. Deploy / seed (ops)

Após alterar permissões ou UI PLATFORM:

```bash
# Rebuild imagens (api e seed compartilham enterprise-template-api)
docker compose up -d --build frontend api
docker compose --profile seed run --rm seed
```

- Seed idempotente sincroniza `PLATFORM` com `platform_only_codes()` (inclui `integration.*`).
- JWT/sessão antiga: fazer **logout/login** como `root` em `ows.*`.
- `docker-compose.yml`: serviços `api` e `seed` usam a mesma `image: enterprise-template-api` para não haver drift de catálogo de permissões.

---

## 16. Arquivos-chave

| Área | Caminho |
|------|---------|
| Página | `frontend/src/pages/IntegrationPage.vue` |
| Layer FE | `frontend/src/layers/integration/` |
| Módulo BE | `backend/src/modules/integrations/` |
| Providers | `backend/src/modules/integrations/providers/` (todos os métodos do roadmap) |
| Webhook inbound | `POST /api/v1/integrations/{id}/webhook/events` |
| Migrations | `0012_integrations`, `0013_integration_webhooks` |
| Permissões FE | `frontend/src/constants/permissions.ts` |
| Rota | `frontend/src/router/index.ts` (`/integrations`) |
| Permissões BE | `backend/src/shared/infrastructure/security/permission_codes.py` |
| Menu PLATFORM | `backend/src/modules/dashboard/providers/platform_provider.py` |
| Seed roles | `backend/scripts/seed.py` (`PLATFORM_PERMISSIONS`) |

---

## 17. Checklist

### ETAPA 1
- [x] `IntegrationPage` + components  
- [x] Layer + Service + Provider stubs  
- [x] Tabela comparativa, cards, form dinâmico, status, logs  
- [x] Mock data (sem rede a terceiros)  
- [x] RBAC visual + permissões platform-only  
- [x] Rota e menu PLATFORM  

### ETAPA 2
- [x] API FastAPI `/api/v1/integrations` (CRUD, test, sync, status, logs)  
- [x] Migration `0012_integrations` + RLS  
- [x] Secrets cifrados (Fernet) — nunca retornados na API  
- [x] `RestProvider` real (httpx): GET/HEAD, headers, auth, timeout, paginação, rate limit, retry  
- [x] Frontend `IntegrationService` → API  
- [x] Testes unitários RestProvider + secrets  

### ETAPA 3
- [x] `OAuth2Provider` Client Credentials (token URL, client id/secret, scope)  
- [x] Cache + renovação de access token no processo do backend (skew 30s)  
- [x] Tokens **nunca** retornados na API / Vue  
- [x] Test/sync do recurso via Bearer obtido no servidor  
- [x] Form UI com Client Secret write-only  

### ETAPA 4
- [x] `MTLSProvider` com client cert + private key + CA (PEM)  
- [x] `ssl.SSLContext` + httpx (`verify=context`)  
- [x] PEMs cifrados no backend; nunca retornados na API  
- [x] Form UI com textareas write-only para PEM  
- [x] Testes com certificados gerados (cryptography)  

### ETAPA 5
- [x] `WebhookProvider` (readiness test + sync push-based)  
- [x] Endpoint inbound `POST /api/v1/integrations/{id}/webhook/events` (HMAC, sem JWT)  
- [x] Eventos `address.created|updated|deleted`  
- [x] Assinatura HMAC-SHA256 (`X-Signature` / `sha256=<hex>`), validação, logs  
- [x] Idempotência + retry de deliveries falhas (`0013_integration_webhooks`)  
- [x] Segredo write-only no form; nunca retornado na API  

### ETAPA 6
- [x] `SFTPProvider` (paramiko) — connect, list, pull CSV  
- [x] Auth password ou private key PEM (+ passphrase opcional), só no backend  
- [x] `remote_path`, `filename_pattern`, `encoding`, `delimiter`  
- [x] `schedule_cron` (metadado) + sync pull via API existente  
- [x] Form UI write-only para senha/chave  
- [x] Testes unitários com paramiko mockado  

### ETAPA 7
- [x] `HttpFileProvider` (httpx) — HEAD/GET + download JSON/CSV  
- [x] Auth none / API key / bearer (secrets no backend)  
- [x] Encoding, delimiter CSV, timeout, retry  
- [x] Form UI write-only para token/API key  
- [x] Testes unitários com MockTransport  

### ETAPA 8
- [x] `SoapProvider` (httpx) — GET WSDL + POST envelope SOAP 1.1  
- [x] Validação de operation no WSDL; SOAPAction; Fault detection  
- [x] Auth none / Basic / Bearer (secrets no backend)  
- [x] Form UI write-only para credenciais  
- [x] Testes unitários com MockTransport  

### ETAPA 9
- [x] `IncrementalSyncProvider` — pull paginado com `cursor_field` / `updated_since`  
- [x] Persistência de `cursor_value` na configuration após Sync  
- [x] Auth none / API key / bearer; page size; timeout  
- [x] Form: cursor read-only + secrets write-only  
- [x] Testes unitários com MockTransport  

### ETAPA 10
- [x] `DatabaseProvider` (asyncpg / PostgreSQL) — **somente leitura**  
- [x] `default_transaction_read_only=on` + transaction `readonly=True`  
- [x] Tabela ou query SELECT/WITH (writes rejeitados); senha write-only  
- [x] Avisos fortes na UI (`DATABASE_WARNING`)  
- [x] Testes unitários com conexão mockada  

---

## 18. Próximo passo

**Roadmap do Integration Hub concluído (ETAPAS 1–10).**

Extensões futuras possíveis sem alterar a Page: MQTT, Kafka, AMQP, GraphQL, gRPC, EDI; worker de schedule para SFTP/`schedule_cron`; binding rico de payload SOAP.
