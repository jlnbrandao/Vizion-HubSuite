# Lanstar Frontend

Vue 3 + Quasar + Pinia + Vue Router + Axios.

## Run

```bash
cd frontend
npm install
npm run dev
```

Abra **http://universe.localhost:9000** (tenant demo).  
Não use `http://localhost:9000` sem subdomínio — o backend resolve o tenant pelo primeiro label do `Host`.

API proxy: `/api` → `http://127.0.0.1:8000` com `changeOrigin: false` (preserva `Host: universe.localhost`).

## Auth

- Access token JWT fica **apenas em memória** (Axios `Authorization: Bearer`).
- Refresh token vive em cookie **httpOnly** (mesmo origin via proxy; `withCredentials: true`).
- No reload, o store chama `/auth/refresh` e hidrata o usuário via `/dashboard/me`.

## Permissions (no role-name branching)

| Piece | Role |
|------|--------|
| `constants/permissions.ts` | Canonical catalog (mirrors backend) |
| `composables/usePermissions.ts` | `can` / `canAny` / `canAll` |
| `stores/dashboard.ts` | Menu/widgets from the API |
| `widgetRegistry.ts` | Resolves `widget_type` → component |
| Router `meta.permissions` | Permission-based guard |

The side menu filters items with `can(item.required_permission)`.
The dashboard renders what the backend composer returns — the UI does not branch on `ADMIN`/`MANAGER`.
