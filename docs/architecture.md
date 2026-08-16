# Architecture — distributable products

OpenVizion is a **Hub (Platform Core)** plus **independent products**. The Hub already lives in `backend/` and `frontend/`. Products live under `products/` and must run without the Hub. GIS is a sellable product whose application code lives **outside** this monorepo; the Hub only catalogs and registers instances.

```
                 OpenVizion
                     │
          ┌──────────┴──────────┐
          │                     │
       PRODUCTS              PLATFORM
          │                     │
   ┌──────┼──────┬──────┐       │
Tracking IoT  SNMP  GIS    Platform Core
```

## Independence rule

If a customer installs Tracking (or GIS) on their own infrastructure, it must work with **no OpenVizion-owned services**. That is `DEPLOYMENT_MODE=standalone` + `PLATFORM_ADAPTER=local`.

The Hub is an optional composition layer: `DEPLOYMENT_MODE=integrated` + `PLATFORM_ADAPTER=hub`.

## What stays in Platform Core

IAM, tenants, RBAC, service catalog, entitlements, billing, integrations, navigation, dashboard. These are **modules of one process**, not microservices.

## What is a product

A product owns its kernel, domain, database, API, frontend, and images. It talks to the Hub only through `HubPlatformAdapter` (HTTP contracts in `packages/contracts`).

Shared Python libraries (no business logic):

| Package | Role |
|---------|------|
| `openvizion-kernel` | PlatformAdapter, authz, entitlements, tenant, audit, Local/Hub adapters |
| `openvizion-events` | EventBusAdapter, LocalEventBus, KafkaEventBus |
| `openvizion-observability` | correlation, JSON logs, /health /ready /version |
| `openvizion-contracts` | versioned Hub ↔ product DTOs |

The Vue package `@openvizion/web-runtime` provides `RuntimeConfig` and auth adapters so the SPA does not scatter `if (mode === 'standalone')`.

## When to extract a module into a separate process

Only if at least one of these is true: independent scale, resource isolation, different availability, different technology, much higher load, independent deploy cadence, security isolation, or a customer must run it on other infrastructure.

## Adding a new product

1. Copy `products/iot` (scaffold) or `products/tracking` (full reference). For an app that already exists, wrap it instead — see below.
2. Own a database (logical DB is enough).
3. Register the slug in Hub `PRODUCT_SERVICES` (`backend/src/modules/services/catalog.py`).
4. Select adapters in the composition root from env vars — never in the domain.
5. Add `deployment/<product>/standalone` and `integrated` compose files (in-repo products). External products keep their own deploy; register the instance under Hub → **Deployments**.

## Wrapping an existing product

GIS is the first case: the app already runs (example: `http://134.209.122.250/login?redirect=/dashboard`). Do **not** port its domain into this repo. Mirror Tracking's composition root (`products/tracking/backend/src/tracking/infrastructure/composition.py`):

1. Depend on `openvizion-kernel`, `openvizion-events`, `openvizion-observability`, `openvizion-contracts` (and `@openvizion/web-runtime` in the SPA).
2. **One** composition root reads `DEPLOYMENT_MODE` / `PLATFORM_ADAPTER` / `PLATFORM_CORE_URL` / `PLATFORM_CLIENT_*` and instantiates `LocalPlatformAdapter` **or** `HubPlatformAdapter`. Domain code must not read `mode`.
3. Standalone: `require_standalone_isolation()` — local adapter, empty `PLATFORM_CORE_URL` (`packages/kernel/src/openvizion/kernel/configuration.py`).
4. Integrated: heartbeat on startup; login / authorize / entitlement via Hub; fail-closed if Hub is down.
5. Process endpoints: `GET /health`, `GET /ready`, `GET /version` (see the IoT scaffold).
6. SPA: `loadRuntimeConfig()` + `createAuthAdapter` — no `if (mode === …)` in components.
7. Tenant still comes from **Host** (or an explicit equivalent). A bare IP with no subdomain needs a mapping (Tracking maps `localhost` → tenant `demo`).

Standalone GIS remains sellable with **no** Hub registration. Deployments inventory and Hub federation are the integrated path only.

Registering a remote instance, probe `/ready`, bind, entitlements and the Hub↔product network caveat: [integrated.md](integrated.md#gis-on-a-remote-vps).
