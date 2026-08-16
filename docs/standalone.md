# Tracking standalone

No Platform Core, no Internet except optional map tiles.

```bash
cd deployment/tracking/standalone
docker compose up --build
```

Services: `tracking-api` (:8100), `tracking-worker`, `tracking-web` (:9100), Postgres (`tracking`), Redis.

Open `http://demo.localhost:9100` (or `http://localhost:9100` — Host `localhost` maps to tenant `demo`).

Login: `admin@demo.local` / `admin123`.

## Env (defaults)

```
DEPLOYMENT_MODE=standalone
PLATFORM_ADAPTER=local
PLATFORM_CORE_URL=
EVENT_BUS_ADAPTER=local
DATABASE_URL=postgresql+asyncpg://tracking:tracking@postgres:5432/tracking
```

`PLATFORM_CORE_URL` **must be empty**. The composition root refuses to start HubPlatformAdapter in this mode.

## Local API without Docker

Install packages then the product (from repo root):

```bash
pip install -e packages/contracts -e packages/observability -e packages/kernel -e packages/events
pip install -e products/tracking/backend
```

Run migrations against a local `tracking` database and `uvicorn tracking.main:app --port 8100`.
