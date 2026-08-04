# Lanstar Frontend

Vue 3 + Quasar + Pinia + Vue Router + Axios.

## Rodar

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:9000  
API proxy: `/api` → `http://localhost:8000`

## Permissões (sem ifs por role)

| Peça | Papel |
|------|--------|
| `constants/permissions.ts` | Catálogo canônico (espelha backend) |
| `composables/usePermissions.ts` | `can` / `canAny` / `canAll` |
| `stores/dashboard.ts` | Menu/widgets vindos da API |
| `widgetRegistry.ts` | Resolve `widget_type` → componente |
| Router `meta.permissions` | Guard por permissão |

O menu lateral filtra itens com `can(item.required_permission)`.
O dashboard renderiza o que o backend composer devolve — a UI não ramifica por `ADMIN`/`MANAGER`.
