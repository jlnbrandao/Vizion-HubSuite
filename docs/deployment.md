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

From the laptop:

```bash
# ~/.ssh/config — already present
# Host vizion-g
#     HostName 209.97.149.171
#     User root
#     IdentityFile ~/.ssh/id_ed25519

./deploy/scripts/remote-deploy.sh --sync        # copy tree to /opt/vizion-h-suite
./deploy/scripts/remote-deploy.sh --bootstrap   # first time: Python 3.13, DB, systemd, nginx :8088
./deploy/scripts/remote-deploy.sh               # later deploys: sync + build + restart
```

| Item | Value |
|------|--------|
| Remote dir | `/opt/vizion-h-suite` |
| API | `127.0.0.1:8010` (`vizion-h-api.service`) |
| UI / proxy | `:8088` (IP) and `https://universe.openvizion.com` / `https://ows.openvizion.com` |
| Postgres / Redis | host services (no Docker); DB name `vizion_hub_prod`, Redis DB `1` |
    
Tenant Host on that VPS: `http://universe.<ip>:8088` (IP form is always allowed). Add a TLS `server_name` later if you point a subdomain at this vhost.
