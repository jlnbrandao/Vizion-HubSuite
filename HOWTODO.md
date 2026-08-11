# HOWTODO — Estender o RBAC em novas implementações

Playbook operacional para autorizar páginas, módulos API (vertical slices), widgets de dashboard e ações de UI no Lanstar.

Autorização é **baseada em códigos de permissão** (`resource.action`). Roles são apenas bolsas de permissões. Nunca proteja feature com `if role == "ADMIN"`.

---

## Modelo mental

```
PermissionCode (resource.action)
        │
        ▼
seed ROLE_PERMISSIONS ──► Postgres (permissions → roles → users)
                                    ▲
JWT carrega só role_ids ────────────┘
        │
        ▼
ResolveEffectiveAccessQuery
        │
        ▼
CurrentUser.permissions
        ├── FastAPI: Depends(require_permission(...))
        ├── Vue Router: meta.permissions
        ├── UI: usePermissions().can(...)
        └── DashboardComposer: provider.required_permission
```

### Regras de ouro

1. Checar **código de permissão**, nunca nome de role, para liberar feature.
2. Manter espelhados o catálogo backend e o frontend (mesmos códigos).
3. Formato obrigatório: `resource.action` — regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`.
4. Usar constantes `PermissionCode.*` — nunca string solta em rotas/UI.
5. O JWT **não** embute permissões; elas são resolvidas a cada request a partir dos `role_ids`.
6. Além do código, registrar **metadados** (resource, action, name, description) no catálogo.
7. Preferir **actions padronizadas** — não inventar verbos.

---

## Metadados da permissão

O código canônico (`users.create`) é o que gates e `can()` checam. Persistimos também metadados para listar, filtrar e gerar UI:

| Campo | Exemplo | Uso |
|-------|---------|-----|
| `id` | UUID | PK / FK em `role_permissions` |
| `code` | `users.create` | Gate AuthZ (`require_permission`, `can`) |
| `resource` | `users` | Filtrar “todas as permissões do recurso X” |
| `action` | `create` | Filtrar por verbo / gerar telas por ação |
| `name` | `Criar usuários` | Label em UI / matriz de roles |
| `description` | `Permite criar usuários` | Ajuda / tooltip |

`resource` e `action` são derivados de `code` (`resource.action`) e armazenados em colunas indexadas. A API devolve os campos e aceita `?resource=` / `?action=` em `GET /api/v1/permissions`.

### Actions padronizadas

Evite inventar verbos. Use `PermissionAction` (backend) / `PermissionAction` (frontend):

| Action | Uso típico |
|--------|------------|
| `create` | Criar registro |
| `read` | Ver detalhe / acessar página |
| `update` | Editar |
| `delete` | Excluir |
| `list` | Listar coleção (quando distinto de `read`) |
| `manage` | Administração ampla do recurso |
| `export` | Exportar dados |
| `import` | Importar dados |
| `approve` | Aprovar fluxo |
| `cancel` | Cancelar fluxo |
| `execute` | Disparar job / ação |
| `assign` | Atribuir vínculo (ex.: `users.assign`, `roles.assign`) |
| `link` / `unlink` | Associar / desassociar |
| `activate` / `deactivate` | Ativar / desativar |

**Exceções de seção:** `dashboard.admin|manager|operator|client|viewer` e `system.settings` são chaves de seção/feature, não verbos CRUD. Não use esse padrão para recursos de domínio novos.

---

## Passo zero — registrar permissão (toda feature nova)

Toda feature protegida começa aqui.

### 1. Backend — catálogo canônico + metadados

Arquivo: [`backend/src/shared/infrastructure/security/permission_codes.py`](backend/src/shared/infrastructure/security/permission_codes.py)

```python
class PermissionCode:
    # ... existentes ...
    REPORTS_READ = "reports.read"
    REPORTS_CREATE = "reports.create"
    REPORTS_EXPORT = "reports.export"

# Em PERMISSION_CATALOG:
PermissionDefinition(
    code=PermissionCode.REPORTS_READ,
    name="Ler relatórios",
    description="Permite visualizar relatórios",
),
PermissionDefinition(
    code=PermissionCode.REPORTS_CREATE,
    name="Criar relatórios",
    description="Permite criar relatórios",
),
PermissionDefinition(
    code=PermissionCode.REPORTS_EXPORT,
    name="Exportar relatórios",
    description="Permite exportar relatórios",
),
```

`PermissionCode.all_codes()` coleta atributos `UPPER` string. O seed usa `PermissionCode.definition_for(code)` para name/description.

### 2. Frontend — espelho

Arquivo: [`frontend/src/constants/permissions.ts`](frontend/src/constants/permissions.ts)

```typescript
export const PermissionCode = {
  // ... existentes ...
  REPORTS_READ: 'reports.read',
  REPORTS_CREATE: 'reports.create',
  REPORTS_EXPORT: 'reports.export',
} as const
```

Para actions novas, reutilize `PermissionAction` (`create`, `export`, …).

### 3. Seed — mapear para roles

Arquivo: [`backend/scripts/seed.py`](backend/scripts/seed.py) — dict `ROLE_PERMISSIONS`.

```python
"MANAGER": frozenset(
    {
        # ... existentes ...
        PermissionCode.REPORTS_READ,
        PermissionCode.REPORTS_EXPORT,
    }
),
"OPERATOR": frozenset(
    {
        # ... existentes ...
        PermissionCode.REPORTS_READ,
        PermissionCode.REPORTS_CREATE,
    }
),
```

**ADMIN é especial:** só CRUD de identity/RBAC + `dashboard.admin`. Não receba `dashboard.manager|operator|client|viewer` nem `system.settings`. O seed valida isso (`FORBIDDEN_FOR_ADMIN`). Se a feature não for administração RBAC, **não** coloque no ADMIN por padrão.

### 4. Aplicar seed

```bash
cd backend
python -m scripts.seed
```

Idempotente: cria permissões faltantes, sincroniza name/description do catálogo e substitui o conjunto de permissões de cada role.

### Alternativa em runtime (admin UI / API)

| Operação | Endpoint | Permissão exigida |
|----------|----------|-------------------|
| Criar permissão | `POST /api/v1/permissions` | `permissions.create` |
| Atribuir a role | `PUT /api/v1/roles/{id}/permissions` | `roles.assign` |
| Atribuir role a usuário | `PUT /api/v1/users/{id}/roles` | `users.assign` |

Features de produto ainda devem entrar no **catálogo + seed**, para o ambiente ser reproduzível.

---

## Cenário A — Nova página Vue

Exemplo: página `/reports` listando relatórios.

### Checklist

1. Passo zero (`reports.read`, etc.).
2. Rota com `meta.permissions`.
3. Botões/ações com `can(...)`.
4. Item de menu via provider do dashboard (Cenário C), se a página deve aparecer no menu.

### Router

Arquivo: [`frontend/src/router/index.ts`](frontend/src/router/index.ts)

```typescript
{
  path: 'reports',
  name: 'reports',
  component: () => import('@/pages/ReportsPage.vue'),
  meta: { permissions: [PermissionCode.REPORTS_READ] },
}
```

O guard exige **todas** as permissões listadas em `meta.permissions`. Sem elas, redireciona para `dashboard`. Rotas filhas do layout já herdam `requiresAuth: true`.

### Controle fino na página

Arquivo padrão: [`frontend/src/composables/usePermissions.ts`](frontend/src/composables/usePermissions.ts)

```vue
<script setup lang="ts">
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'

const { can } = usePermissions()
</script>

<template>
  <q-btn
    v-if="can(PermissionCode.REPORTS_CREATE)"
    label="Novo relatório"
  />
  <q-btn
    v-if="can(PermissionCode.REPORTS_EXPORT)"
    label="Exportar"
  />
</template>
```

A página pode exigir só `reports.read` no router; create/export ficam só no botão **e** no endpoint correspondente (Cenário D).

### O que não fazer

```typescript
// ERRADO
if (auth.user?.roleNames.includes('ADMIN')) { ... }
```

---

## Cenário B — Novo módulo API (vertical slice)

O Lanstar é um **monólito modular**. Um “microsserviço” interno = novo slice em `backend/src/modules/<nome>/`, não um processo separado. AuthZ é o mesmo gateway FastAPI.

### Checklist

1. Passo zero (códigos `resource.action`).
2. Criar módulo: commands, queries, handlers, routes, schemas (seguir `users` / `roles` / `permissions`).
3. Gate em **cada** endpoint com `Depends(require_permission(...))`.
4. Registrar handler no DI + `register_module_handlers`.
5. Montar router em `main.py`.
6. Espelhar códigos no frontend se a UI chamar a API.

### Gate nas rotas

Arquivo de referência: [`backend/src/modules/users/routes/user_routes.py`](backend/src/modules/users/routes/user_routes.py)

Helpers em [`backend/src/shared/infrastructure/security/dependencies.py`](backend/src/shared/infrastructure/security/dependencies.py):

| Helper | Semântica |
|--------|-----------|
| `require_permission(*codes)` | Exige **todas** as permissões |
| `require_any_permission(*codes)` | Exige **pelo menos uma** |
| `get_current_user` | Só autenticação (sem AuthZ de permissão) |
| `require_any_role(...)` | Existe, mas **evitar** para features — preferir permissões |

```python
from src.shared.infrastructure.security.dependencies import require_permission
from src.shared.infrastructure.security.permission_codes import PermissionCode
from src.shared.infrastructure.security.current_user import CurrentUser

router = APIRouter(prefix="/reports", tags=["reports"])

@router.get("")
@inject
async def list_reports(
    query_bus: QueryBus = Depends(Provide[Container.query_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.REPORTS_READ)),
) -> list[ReportResponse]:
    ...

@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def create_report(
    body: CreateReportRequest,
    command_bus: CommandBus = Depends(Provide[Container.command_bus]),
    _: CurrentUser = Depends(require_permission(PermissionCode.REPORTS_CREATE)),
) -> ReportIdResponse:
    ...
```

Sem permissão → `403 Forbidden` (`ForbiddenError`).

### Wiring do módulo

1. **Container** — providers de repository/handlers em [`backend/src/shared/infrastructure/di/container.py`](backend/src/shared/infrastructure/di/container.py).
2. **Buses** — mapear Command/Query → Handler em [`backend/src/shared/infrastructure/di/register_handlers.py`](backend/src/shared/infrastructure/di/register_handlers.py).
3. **HTTP** — `app.include_router(reports_router, prefix="/api/v1")` em [`backend/src/main.py`](backend/src/main.py).

### Comunicação entre módulos

Commands, Queries, Domain Events e interfaces — **nunca** importar entidades internas de outro módulo.

---

## Cenário C — Nova seção de dashboard / widget

O menu e os widgets são **compostos no backend**. A UI renderiza o que a API devolve; não ramifica por role.

### Checklist

1. Passo zero — tipicamente `dashboard.<section>` (ex.: `dashboard.reports`), **ou** reutilizar um `dashboard.*` existente.
2. Implementar `DashboardSectionProvider`.
3. Registrar no `DashboardComposer` (container).
4. Se `widget_type` for novo: componente Vue + entrada no registry.
5. Incluir itens de menu com `required_permission` da página-alvo.

### Provider

Contrato: [`backend/src/modules/dashboard/providers/base.py`](backend/src/modules/dashboard/providers/base.py)

Referência: [`backend/src/modules/dashboard/providers/admin_provider.py`](backend/src/modules/dashboard/providers/admin_provider.py)

```python
class ReportsDashboardProvider(DashboardSectionProvider):
    @property
    def required_permission(self) -> str:
        return PermissionCode.DASHBOARD_OPERATOR  # ou dashboard.reports novo

    async def build_menu(self, user: CurrentUser) -> list[DashboardMenuItem]:
        return [
            DashboardMenuItem(
                id="reports-list",
                label="Relatórios",
                route="/reports",
                icon="assessment",
                required_permission=PermissionCode.REPORTS_READ,
            ),
        ]

    async def build_widgets(self, user: CurrentUser) -> list[DashboardWidget]:
        return [
            DashboardWidget(
                id="reports-summary",
                title="Relatórios",
                widget_type="stats",  # tipo já existente
                data={"reports_total": 42},
            ),
        ]
```

O composer só ativa o provider se `user.has_permission(provider.required_permission)`.

### Registrar no DI

Em [`container.py`](backend/src/shared/infrastructure/di/container.py):

```python
reports_dashboard_provider: providers.Singleton[ReportsDashboardProvider] = (
    providers.Singleton(ReportsDashboardProvider)
)

dashboard_composer: providers.Singleton[DashboardComposer] = providers.Singleton(
    DashboardComposer,
    providers=providers.List(
        admin_dashboard_provider,
        # ...
        reports_dashboard_provider,
    ),
)
```

### Novo `widget_type` no frontend

1. Criar `frontend/src/components/dashboard/widgets/ReportsChartWidget.vue`.
2. Registrar em [`frontend/src/components/dashboard/widgetRegistry.ts`](frontend/src/components/dashboard/widgetRegistry.ts):

```typescript
const registry: Record<string, Component> = {
  // ... existentes ...
  reports_chart: defineAsyncComponent(
    () => import('@/components/dashboard/widgets/ReportsChartWidget.vue'),
  ),
}
```

3. No provider, usar `widget_type="reports_chart"`.

O menu lateral (`MainLayout`) ainda filtra itens com `can(item.required_permission)` — o backend envia o código; o frontend esconde o que o usuário não tem.

---

## Cenário D — Controle fino (só botão / ação)

Quando a página já existe e você precisa proteger uma ação pontual.

### Checklist

1. Passo zero — permissão específica (ex.: `users.assign`, `reports.export`).
2. Endpoint backend com o **mesmo** código.
3. Router da página continua com a permissão de leitura (ex.: `users.read`).
4. Botão: `v-if="can(PermissionCode.…)"`.

### Padrão real (Users)

| Camada | Código |
|--------|--------|
| Router | `meta.permissions: [USERS_READ]` |
| Botão criar | `can(USERS_CREATE)` |
| Botão editar | `can(USERS_UPDATE)` |
| Botão roles | `can(USERS_ASSIGN)` |
| Botão excluir | `can(USERS_DELETE)` |
| API | cada rota com o `require_permission` correspondente |

Esconder o botão **não** substitui o gate no backend. Sempre os dois.

---

## Referência rápida — arquivos-chave

| Peça | Caminho |
|------|---------|
| Catálogo backend (+ metadados / actions) | `backend/src/shared/infrastructure/security/permission_codes.py` |
| Catálogo frontend (+ `PermissionAction`) | `frontend/src/constants/permissions.ts` |
| Seed / mapa role→perms | `backend/scripts/seed.py` |
| CurrentUser | `backend/src/shared/infrastructure/security/current_user.py` |
| Depends AuthZ | `backend/src/shared/infrastructure/security/dependencies.py` |
| Resolução efetiva | `backend/src/modules/authentication/handlers/access_handlers.py` |
| Provider dashboard | `backend/src/modules/dashboard/providers/base.py` |
| Composer | `backend/src/modules/dashboard/services/dashboard_composer.py` |
| DI / providers | `backend/src/shared/infrastructure/di/container.py` |
| Register handlers | `backend/src/shared/infrastructure/di/register_handlers.py` |
| Mount routers | `backend/src/main.py` |
| Router guard | `frontend/src/router/index.ts` |
| `can` / `canAny` / `canAll` | `frontend/src/composables/usePermissions.ts` |
| Session / permissões | `frontend/src/stores/auth.ts` (via `GET /dashboard/me`) |
| Widget registry | `frontend/src/components/dashboard/widgetRegistry.ts` |

---

## Catálogo atual e roles do seed

### Permissões canônicas

| Resource | Actions |
|----------|---------|
| `users` | `create`, `read`, `update`, `delete`, `assign` |
| `roles` | `create`, `read`, `update`, `delete`, `assign` |
| `permissions` | `create`, `read`, `update`, `delete` |
| `dashboard` | `admin`, `manager`, `operator`, `client`, `viewer` |
| `system` | `settings` (no catálogo; **não** atribuída a nenhuma role do seed) |

### Mapa seed (resumo)

| Role | Escopo |
|------|--------|
| **ADMIN** | CRUD users/roles/permissions + `dashboard.admin` apenas |
| **MANAGER** | `users.read/update`, `roles.read`, `permissions.read`, `dashboard.manager` |
| **OPERATOR** | `users.read`, `dashboard.operator` |
| **CLIENT** | `dashboard.client` |
| **VIEWER** | `users/roles/permissions.read`, `dashboard.viewer` |

Demo users (password `123Mudar.`):

| username | email | role |
|---|---|---|
| `galileu` | `galileu@lanstar.com.br` | `ADMIN` |
| `manager` | `manager@lanstar.com.br` | `MANAGER` |
| `operator` | `operator@lanstar.com.br` | `OPERATOR` |
| `user` | `user@lanstar.com.br` | `CLIENT` |
| `viewer` | `viewer@lanstar.com.br` | `VIEWER` |

---

## Checklist pós-implementação

- [ ] Código adicionado em `permission_codes.py` **e** `permissions.ts` (mesmos valores).
- [ ] Metadados em `PERMISSION_CATALOG` (name + description); action preferencialmente de `PermissionAction`.
- [ ] Código incluído em `ROLE_PERMISSIONS` nas roles corretas (respeitar regra do ADMIN).
- [ ] `python -m scripts.seed` executado no ambiente.
- [ ] Endpoints API com `Depends(require_permission(...))` (ou `require_any_permission`).
- [ ] Página Vue com `meta.permissions` (se for rota nova).
- [ ] Botões/ações com `v-if="can(...)"` — sem `if` por nome de role.
- [ ] Provider de dashboard registrado no `DashboardComposer` (se menu/widgets).
- [ ] `widget_type` novo registrado em `widgetRegistry.ts` (se aplicável).
- [ ] Router do módulo montado em `main.py` + handlers no DI/buses (módulo novo).
- [ ] Teste manual:
  - usuário **com** permissão → 200 / página / botão visível;
  - usuário **sem** permissão → 403 na API, redirect no router, botão oculto.

---

## Fluxo mínimo sugerido (feature completa)

Para um recurso novo de ponta a ponta (ex.: Relatórios):

1. Definir códigos (`reports.read`, `reports.create`, … + opcional `dashboard.reports`).
2. Seed nas roles.
3. Módulo API + gates.
4. Página Vue + `meta` + `can()`.
5. Provider de menu/widgets.
6. Seed + login com role de teste + validar positivo/negativo.
