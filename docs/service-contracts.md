# Service contracts

Prefer OpenAPI, DTOs and events. Do not import another product's internals.

## Hub admin (JWT user, `platform.products.*`)

| Method | Path |
|--------|------|
| GET | `/api/v1/products/topology` |
| GET/POST | `/api/v1/products/instances` |
| GET/PATCH | `/api/v1/products/instances/{id}` |
| POST | `/api/v1/products/instances/{id}/probe` |
| POST | `/api/v1/products/instances/{id}/deactivate` |
| GET/PUT | `/api/v1/products/instances/{id}/bindings` |

## Hub product API (service JWT)

| Method | Path |
|--------|------|
| POST | `/api/v1/hub/token` |
| POST | `/api/v1/hub/heartbeat` |
| POST | `/api/v1/hub/introspect` |
| POST | `/api/v1/hub/authorize` |
| POST | `/api/v1/hub/entitlements/check` |
| POST | `/api/v1/hub/audit` |
| POST | `/api/v1/hub/events` |
| GET | `/api/v1/hub/tenants/{id}` |

These routes skip Host tenant resolution (service-to-service).

## Tracking API `/api/v1`

`/auth/login`, `/auth/me`, `/devices`, `/vehicles`, `/positions`, `/geofences`.

Health (every process): `GET /health` (liveness), `GET /ready` (needed deps only), `GET /version`.
