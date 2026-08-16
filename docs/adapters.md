# Adapters

Selection happens **only** in the composition root (`products/tracking/backend/src/tracking/infrastructure/composition.py`). Domain code depends on protocols from `openvizion.kernel` and `openvizion.events`.

## PlatformAdapter

| Mode | Class | Network |
|------|-------|---------|
| standalone | `LocalPlatformAdapter` | none |
| integrated | `HubPlatformAdapter` | `PLATFORM_CORE_URL` |

Switch: `PLATFORM_ADAPTER=local|hub`.

## EventBusAdapter

| Adapter | Class | When |
|---------|-------|------|
| `local` | `LocalEventBus` | default, including standalone |
| `kafka` | `KafkaEventBus` | optional; injects a producer (aiokafka in production, fake in tests) |

Switch: `EVENT_BUS_ADAPTER=local|kafka`.

## Storage / cache / notifications

Ports exist conceptually. Tracking v1 persists via SQLAlchemy repositories (infrastructure only) and does not call S3. Add `StorageAdapter` when a product actually needs object storage.

## Frontend

`loadRuntimeConfig()` reads `/config.json`. `createAuthAdapter(config, http)` returns Local or Hub adapters that both call **the product API**. Hub federation is server-side. Components must not read `mode`.
