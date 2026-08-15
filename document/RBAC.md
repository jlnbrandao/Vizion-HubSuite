# HubSuite — RBAC (Role-Based Access Control)

RBAC responde: **este papel tem o código desta ação?** Não sabe de recurso individual — isso é [ACL.md](ACL.md). Não sabe de IP, dono ou horário — isso é [ABAC.md](ABAC.md).

| | |
|---|---|
| **Catálogo** | [permission_codes.py](../backend/src/shared/infrastructure/security/permission_codes.py) |
| **Hierarquia** | [role_hierarchy.py](../backend/src/shared/infrastructure/security/role_hierarchy.py) + `HierarchyPolicy` |
| **Engine** | estágio 5 em [AUTHORIZATION.md](AUTHORIZATION.md) |
| **UI** | Users / Roles / Permissions / Bundles em `frontend/src/modules/iam/` |

---

## 1. Modelo

```
Permission (service.resource.action  +  alias legado resource.action)
        ↑
 PermissionBundle  ⇄  Permissions
        ↑
      Role  ⇄  Bundles  +  role_permissions (exceções finas)
        ↑
      User  ⇄  Roles
```

Permissões efetivas = união dos códigos das roles + códigos dos **bundles** das roles (`role_permission_groups`), cada um expandido nos dois formatos (`PermissionCode.expand()`).

---

## 2. Códigos

Formato canônico: `service.resource.action` (`iam.users.read`).  
Formato legado: `resource.action` (`users.read`) — **ainda válido**. Quem tem um tem o outro.

| Conceito | Onde |
|----------|------|
| Definição (canônico + legado + serviço) | `PermissionDefinition` |
| Recurso → serviço (2 segmentos) | `SERVICE_BY_RESOURCE` |
| Bundles semeados | `PERMISSION_BUNDLES` |
| Só na plataforma | `PermissionCode.platform_only_codes()` |

Serviços do catálogo:

| Serviço | Recursos (exemplos) |
|---------|---------------------|
| `iam` | users, roles, permissions, permission_groups, dashboard, system, audit, sessions, oauth_clients, service_accounts, api_keys, federation, policies, acl, scim |
| `platform` | tenants, services, usage |
| `integration` | integration |

O frontend **não** escreve código à mão. Gerar o espelho:

```bash
cd backend && python -m scripts.generate_frontend_permissions
```

Saída: `frontend/src/constants/permissions.ts`.

---

## 3. Bundles

Uma role é “IAM admin”, não 40 checkboxes. Bundles do seed:

| Bundle | Destino típico |
|--------|----------------|
| `iam.admin` | `ADMIN` |
| `iam.manager` | `MANAGER` |
| `iam.operator` | `OPERATOR` |
| `iam.client` | `CLIENT` |
| `iam.viewer` | `VIEWER` |
| `platform.admin` | `PLATFORM` (tenant `ows`) |
| `integration.admin` | `PLATFORM` |

`role_permissions` continua para exceções finas (um código a mais ou a menos sem criar bundle).

Códigos **platform-only** (`tenants.*`, `services.*`, `usage.read_all`, `system.settings`, `dashboard.platform`, `integration.*`) existem só no tenant `ows`, não no RBAC de produto.

---

## 4. Hierarquia

Única tabela de privilégio para *quem gerencia quem*:

`PLATFORM (200) > ADMIN (100) > MANAGER (80) > OPERATOR (60) > CLIENT (40) > VIEWER (20)`

Quem gerencia usuários, roles ou permissões precisa **superar estritamente** o alvo. Pares e superiores são intocáveis. Roles customizadas sem nome conhecido têm rank 0.

A comparação vive em `HierarchyPolicy` no engine; `ROLE_RANK` é só a tabela (evita ciclo de import).

---

## 5. Seed

**Tenant `universe`:** roles `ADMIN`, `MANAGER`, `OPERATOR`, `CLIENT`, `VIEWER`.  
**Tenant `ows`:** role `PLATFORM` (usuário `root`). Sem `ADMIN` neste tenant — em `/tenants` o campo `admin` fica `null`.

---

## 6. Como usar

1. Rota: `Depends(require_permission(PermissionCode.USERS_READ))` — nunca `if user.role == "ADMIN"`.
2. Código novo entra em `permission_codes.py` (e em `SERVICE_BY_RESOURCE` se o recurso é novo) **antes** de ser referenciado.
3. Sem `ResourceRef`, o engine avalia RBAC (e tenant/entitlement) e **omite** ACL/ABAC — é o caso das rotas de coleção.
4. Guard Vue (`can` / `meta.permissions`) espelha UX.

Testes: [test_authorization_service.py](../backend/tests/unit/shared/security/test_authorization_service.py), [test_authorization_matrix.py](../backend/tests/integration/test_authorization_matrix.py).
