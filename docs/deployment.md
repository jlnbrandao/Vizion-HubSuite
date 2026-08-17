# Deployment

Docker Compose is the supported first deployment. Kubernetes is intentionally out of scope.

## Images

| Image | Source |
|-------|--------|
| Hub API | `backend/Dockerfile` |
| Hub web | `frontend/Dockerfile` |
| `openvizion/tracking-api` | `products/tracking/backend/Dockerfile` |
| `openvizion/tracking-worker` | same image, `python -m tracking.worker` |
| `openvizion/tracking-web` | `products/tracking/frontend/Dockerfile` |
| `openvizion/iot-api` | `products/iot/backend/Dockerfile` |
| `openvizion/snmp-api` | `products/snmp/backend/Dockerfile` |

## Layouts

### Small (one VPS)

Run Hub compose at the repo root **or** Tracking standalone under `deployment/tracking/standalone`. All processes share the host; each product still uses its **own database name**.

### Medium (several VPS)

Point `PLATFORM_CORE_URL` at the Hub host. Open only TLS ports. Register the product in Hub → **Deployments** (host, IP, ports, environment). Set `PLATFORM_CLIENT_ID` / `PLATFORM_CLIENT_SECRET` to the values stored in that registry. GIS is registered the same way (slug `gis`); its images are not built from this repo — see [integrated.md](integrated.md#gis-on-a-remote-vps).

### Large

Same contracts, more replicas, optional `EVENT_BUS_ADAPTER=kafka`. No cluster orchestrator is required to prove the architecture.

## Environment

Never put secrets in the frontend. Runtime UI config is `/config.json` (mode, API URL). Service secrets stay in API env vars.

See [standalone.md](standalone.md) and [integrated.md](integrated.md).

## Remote host (`ssh vizion-g`)

The GPS VPS already runs Vizion-G on `/opt/vizion-g-*`, nginx for `openvizion.com`, and the API on port **8000**. Do **not** run `deploy/scripts/install.sh` there (it would take `default_server` and port 8000).

HubSuite lives beside it: `/opt/vizion-h-suite`, API on **8010**, nginx vhost **exact** names `universe.openvizion.com` and `ows.openvizion.com` (those beat the Vizion-G regex `*.openvizion.com`). Other tenant slugs stay on Vizion-G.

[https://lanstar.openvizion.com](https://lanstar.openvizion.com) is **not** HubSuite: nginx proxies to the Lanstar app on `134.209.122.250` (`deploy/nginx/lanstar.openvizion.com.conf`). Login there uses Lanstar’s tenant field (e.g. the owner tenant). That proxy is registered as a **Lanstar** row on Deployments (`/platform/products`) when `LANSTAR_ORIGIN_HOST` is set and seed runs.

From the laptop (`Host vizion-g` in `~/.ssh/config` → `209.97.149.171`, user `root`):

```bash
./deploy/scripts/remote-deploy.sh --sync        # copy tree to /opt/vizion-h-suite
./deploy/scripts/remote-deploy.sh --bootstrap   # first time: Python 3.13, DB, systemd, nginx
./deploy/scripts/remote-deploy.sh               # later deploys: sync + build + restart
```

`rsync` is preferred (supports `--delete`). Without it the script falls back to `tar`+`ssh`.

| Item | Value |
|------|--------|
| Remote dir | `/opt/vizion-h-suite` |
| API | `127.0.0.1:8010` (`vizion-h-api.service`) |
| UI | [https://universe.openvizion.com](https://universe.openvizion.com) / [https://ows.openvizion.com](https://ows.openvizion.com) |
| Lanstar | [https://lanstar.openvizion.com](https://lanstar.openvizion.com) → `134.209.122.250` |
| Fallback | `:8088` by IP (`http://universe.<ip>:8088`) |
| Postgres | host service, database **`vizion_hub_prod`** (not `vizion_g_prod`) |
| Redis | host service, DB `1` |
| Nginx | `deploy/nginx/vizion-h.conf` → `/etc/nginx/sites-enabled/vizion-h.conf` |

### First login (seed)

`--bootstrap` does **not** create users. After migrations:

```bash
ssh vizion-g 'cd /opt/vizion-h-suite/backend && SEED_ALLOW_INSECURE=true .venv/bin/python -m scripts.seed'
```

| Host | User | Role |
|------|------|------|
| `universe.openvizion.com` | `admin` | `ADMIN` |
| `ows.openvizion.com` | `root` | `PLATFORM` |

Demo password is `SEED_PASSWORD` in `backend/scripts/seed.py`.

### Postgres on a shared VPS

`vizion` is **not** a superuser here (unlike Docker Compose). Two consequences:

1. Alembic wraps migrations with `SET LOCAL app.rls_bypass = on` (`backend/alembic/env.py`).
2. `resolve_tenant_by_slug` must run with `SET app.rls_bypass = on` (migration `0023`, applied as `postgres`). Without that, login returns **404 Unknown tenant** even though the row exists. See [document/RLS.md](../document/RLS.md).
