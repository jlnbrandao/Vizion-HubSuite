# Tracking integrated (Hub)

```bash
cd deployment/tracking/integrated
docker compose up --build
```

This starts Platform Core (`:8000` / `:9000`) and Tracking (`:8100` / `:9100`) on the **same Postgres server**, different databases (`vizion` vs `tracking`).

## Wiring

```
tracking-api  →  HubPlatformAdapter  →  platform-core /api/v1/hub/*
```

1. Seed / log into Hub as platform admin (`ows.localhost:9000`).
2. Open **Deployments** (`/platform/products`).
3. Register Tracking:
   - slug `tracking`
   - API URL `http://tracking-api:8000` (compose DNS) or the public URL
   - client id `tracking-local`
   - client secret `tracking-client-secret` (must match Tracking env)
4. Probe `/ready` + `/version`.
5. Bind a product tenant (e.g. `universe`) to the instance.
6. Entitle the tenant to service `tracking` under **Service entitlements**.
7. Open the Tracking UI; login federates credentials to Hub and issues a Tracking JWT.

## Env

```
DEPLOYMENT_MODE=integrated
PLATFORM_ADAPTER=hub
PLATFORM_CORE_URL=http://platform-core:8000
PLATFORM_CLIENT_ID=tracking-local
PLATFORM_CLIENT_SECRET=...
EVENT_BUS_ADAPTER=local
```

Kafka is optional (`EVENT_BUS_ADAPTER=kafka` + `KAFKA_BOOTSTRAP_SERVERS`). Integrated compose uses the local bus by default.

## Failure behaviour

Hub timeouts and 5xx are retried briefly, then **fail-closed** for authorize/entitlement. Login cannot succeed if Hub is down.

## GIS on a remote VPS

GIS is a Hub catalog slug (`gis`), not an image in this repo. After `alembic upgrade head` (migration `0022`) and seed, log into `ows.localhost:9000` as platform admin and open **Deployments** (`/platform/products`) → **Register instance**.

Example — GIS at `http://134.209.122.250/login?redirect=/dashboard`:

| Field | Typical value |
|-------|----------------|
| Product | `gis` |
| Name | e.g. `GIS DigitalOcean` |
| Environment | Remote VPS |
| Scheme | `http` (switch to `https` once TLS is on) |
| Host / IP | `134.209.122.250` |
| API port | the **API** port (if nginx only serves the SPA on `:80`, do not guess — use the real API port) |
| UI host / UI port | `134.209.122.250` / `80` |
| Notes | region, droplet, compose project |
| Client ID / secret | a new pair; the **same** values go into GIS env as `PLATFORM_CLIENT_ID` / `PLATFORM_CLIENT_SECRET` when integrated |

Then:

1. Bind a product tenant (e.g. `universe`) to that instance.
2. Entitle the tenant to service `gis` under **Service entitlements**.
3. Re-seed if `gis` is missing from the catalog (`docker compose --profile seed run --rm seed`).

**Probe** issues `GET {base_url}/ready` from the Hub process. Registration succeeds without it. Probe fails until GIS exposes `/ready` **and** the DigitalOcean firewall allows the Hub host.

### Network

Registering GIS on a **local** Hub (`ows.localhost`) is inventory only. Heartbeat and federated login need the GIS process to **reach the Hub**. `http://127.0.0.1:8000` on a developer laptop is not visible from DigitalOcean.

- Inventory now: local Hub + the form above.
- Real federation: Hub URL the VPS can call (public Hub, or Hub on the same VPS) in `PLATFORM_CORE_URL`. Open UI 80/443, the API port, Hub → GIS for probe, GIS → Hub `/api/v1/hub/*`.

Adapter wrap of the existing GIS codebase: [architecture.md](architecture.md#wrapping-an-existing-product).

