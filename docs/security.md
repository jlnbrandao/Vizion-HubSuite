# Security

- Standalone: local JWT (HS256) issued by the product kernel.
- Integrated: Hub verifies user credentials; the product issues its own JWT after Hub introspect. Service-to-service calls use a **service JWT** (`token_use=service`) obtained with registered `client_id` / `client_secret`.
- Secrets: environment / secret manager only. Never in the SPA.
- TLS: required for remote Hub URLs in production (`https://`).
- Tenant isolation in repositories; Hub tables keep RLS where they are tenant-scoped.
- `product_instances` is platform-global (no tenant_id); only `platform.products.*` may manage it.
- Audit actions go through `PlatformAdapter.audit` (local table or Hub `/hub/audit`).
- Do not log passwords, tokens, or client secrets. Correlation fields: `request_id`, `correlation_id`, `tenant_id`, `user_id`, `service`.
- Least privilege: Tracking roles ADMIN / OPERATOR / VIEWER map to namespaced `tracking.*` codes.
