"""Skeleton of a Hub service slice. Copy this folder to start a new service.

Checklist — see `document/SERVICE_HUB.md` for the full contract:

1. Rename the package to the service slug (`gps`, `snmp`, `ddns`, ...).
2. Register the service in the catalog: a row in `services` with `slug`,
   `namespace` and version (migration or `scripts/seed.py`).
3. Declare permissions only inside your namespace (`gps.vehicles.read`) in
   `shared/infrastructure/security/permission_codes.py`, then regenerate the
   frontend constants with `python -m scripts.generate_frontend_permissions`.
4. Every table carries `tenant_id`, has `FORCE ROW LEVEL SECURITY` and the
   standard tenant isolation policy.
5. Guard routes with `require_permission(...)` only — never re-implement
   authorization; the engine already applies tenant, entitlement, ACL, RBAC and
   ABAC in that order.
6. Meter what you sell with `ServiceQuotaGuard.enforce(...)`.
7. Emit audit events for state changes through `AuditService`.
8. Add the frontend slice under `frontend/src/modules/<slug>/` with its own
   `routes.ts` carrying `meta.service` and `meta.permissions`, and add the menu
   entries to `src/modules/navigation/catalog.py`.

This package is intentionally not registered in `main.py`.
"""
