# HubSuite — ABAC (Attribute-Based Access Control)

ABAC responde com atributos do **sujeito**, do **recurso** e do **ambiente**. No HubSuite ele é o **último** estágio do engine e **só nega**: nunca concede sozinho o que o RBAC recusou. Ver [AUTHORIZATION.md](AUTHORIZATION.md).

| | |
|---|---|
| **Tabela** | `access_policies` |
| **Enforcer** | [iam/abac/service.py](../backend/src/modules/iam/abac/service.py) (`PolicyEnforcer`) |
| **Ponte** | `AbacServiceGate` em [authorization_adapters.py](../backend/src/shared/infrastructure/security/authorization_adapters.py) |
| **Flag** | `IAM_ABAC_ENABLED` (default `true`) |
| **UI** | Policies em `frontend/src/modules/iam/` |

`casbin` está nas dependências do backend, mas **não** é o enforcer em runtime. A avaliação é o `PolicyEnforcer` sobre as linhas de `access_policies`.

---

## 1. Quando roda

O estágio 6 só existe se a checagem trouxe um `ResourceRef` (recurso concreto). Rotas de coleção (`require_permission` sem recurso) **não** passam por ABAC.

Se `IAM_ABAC_ENABLED=false`, ou se não houver sessão de banco no request, o gate **abstém** (devolve allow) e a decisão fica com os estágios anteriores.

ACL allow (estágio 4) curto-circuita o ABAC de propósito.

---

## 2. Modelo de policy

| Campo | Uso |
|-------|-----|
| `tenant_id` | RLS; policy de um tenant não vale em outro |
| `name` / `description` | identificação |
| `effect` | `allow` ou `deny` (no engine, deny/falha de allow-gate **barra**; allow da policy não cria permissão nova) |
| `actions` | códigos ou `*`; vazio = qualquer ação |
| `resource_types` | tipos do `ResourceRef` ou `*`; vazio = qualquer tipo |
| `conditions` | JSON de predicados (abaixo) |
| `priority` | menor número primeiro |
| `is_active` | inativa é ignorada |

Sem policy aplicável, o enforcer devolve **true** (não interfere no RBAC).

---

## 3. Condições suportadas

Implementadas em `PolicyEnforcer._match`:

| Chave | Significado |
|-------|-------------|
| `min_role_rank` | rank máximo das roles do sujeito ≥ valor |
| `subject_outranks_target` | sujeito precisa superar as roles do alvo (`target_role_names` no `ResourceRef`) |
| `ip_in_allowlist` | `RequestContext.ip` precisa estar na lista |
| `resource_owner_is_subject` | `resource.owner_id == subject.user_id` |

Ranks usados **neste** enforcer (tabela local, distinta de `ROLE_RANK` do RBAC):

`PLATFORM 100`, `ADMIN 80`, `MANAGER 60`, `OPERATOR 40`, `CLIENT 20`, `VIEWER 10`.

Allow-gate com `subject_outranks_target` que **não** casa → deny. É assim que “não gerencie um par ou superior” entra no engine quando há `ResourceRef` do alvo.

Ambiente (`RequestContext`): `ip`, `user_agent`, mais `extra`.

---

## 4. API

| Método | Rota | Permissão |
|--------|------|-----------|
| `GET` | `/api/v1/access-policies` | `iam.policies.read` |
| `POST` | `/api/v1/access-policies` | `iam.policies.create` |

Update/delete existem no serviço (`AbacService`) e nas permissões `iam.policies.update` / `iam.policies.delete`.

Negativa no engine: `Decision(stage=abac)` e evento `AUTHZ_DENIED`.

---

## 5. Regras

- **ABAC não substitui RBAC.** Sem o código da role, a request já morreu no estágio 5.
- **Prefira condição estreita.** Policy `effect=allow` + `actions=["*"]` sem condição é ruído: o RBAC já autorizou.
- **Deny contextual** (IP, dono, rank) é o uso certo.
- Tenant isolation (estágio 1) e RLS continuam acima: policy não fura tenant.

Por que só nega no engine: uma policy mal gravada que *concedesse* sozinha seria escalonamento de privilégio. Decisão consciente em [SECURITY.md](SECURITY.md).
