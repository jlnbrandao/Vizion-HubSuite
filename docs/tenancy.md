# Tenancy

Every product isolates tenants itself. The Hub is not the only isolation boundary.

Flow:

```
Authentication → Tenant Context (Host) → Authorization → Use case → Repository (tenant_id filter)
```

- `tenant_id` comes from the authenticated principal / Host slug.
- Request bodies must not choose the tenant.
- Tracking tables `devices`, `positions`, `vehicles`, `geofences` all have `tenant_id`.
- Repositories return `None` when the row belongs to another tenant.

Standalone Tracking resolves Host:

- `localhost` / `127.0.0.1` → tenant `demo`
- `demo.localhost` → `demo`

Hub tenants continue to use the first Host label (`universe`, `ows`, …) as today.
