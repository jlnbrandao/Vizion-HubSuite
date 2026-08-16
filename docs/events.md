# Events

Envelope (`openvizion.contracts.events.EventEnvelope`):

```
event_id, event_type, occurred_at, tenant_id, correlation_id, request_id, producer, payload
```

Tracking publishes:

| Type | When |
|------|------|
| `tracking.PositionReceived` | new position ingest (not on idempotent replay) |
| `tracking.GeofenceEntered` | worker |
| `tracking.GeofenceExited` | worker |

Standalone: in-process `LocalEventBus`. Integrated: same, plus optional forward to Hub `POST /api/v1/hub/events`. Kafka: `KafkaEventBus` writes to `{prefix}.{event_type}`.

Position ingest is idempotent on `(tenant_id, event_id)`.
