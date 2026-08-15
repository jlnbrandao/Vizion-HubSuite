# Vizion — ACL por recurso

RBAC responde "esse papel pode editar usuários?". ACL responde "esse usuário pode editar **este** usuário?". É a exceção pontual: um deny cirúrgico ou um allow sobre um recurso específico, sem mexer em role nenhuma.

| | |
|---|---|
| **Tabela** | `resource_acls` — migration [0014_resource_acls.py](../backend/alembic/versions/0014_resource_acls.py) |
| **Modelo** | `ResourceAclModel` em [iam/models.py](../backend/src/modules/iam/models.py) |
| **Serviço** | [iam/acl/service.py](../backend/src/modules/iam/acl/service.py) |
| **Ponte com o engine** | `AclServiceProvider` em [authorization_adapters.py](../backend/src/shared/infrastructure/security/authorization_adapters.py) |
| **UI** | [modules/iam/pages/AclPage.vue](../frontend/src/modules/iam/pages/AclPage.vue) |

---

## 1. Modelo

| Coluna | Conteúdo |
|--------|----------|
| `tenant_id` | dono da entrada; RLS forçado, uma ACL nunca cruza tenant |
| `subject_type` / `subject_id` | `user` ou `role` |
| `resource_type` / `resource_id` | tipo lógico (`user`, `integration`, …) e id (string, aceita chave não-UUID) |
| `action` | código de permissão avaliado (`iam.users.update` ou o alias legado) |
| `effect` | `allow` ou `deny` |
| `expires_at` | opcional; entradas vencidas são ignoradas na avaliação |
| `granted_by` | quem concedeu — rastreabilidade |

`(tenant, subject, resource, action)` é único: conceder de novo **atualiza** a entrada (efeito, validade, autor) em vez de duplicar.

---

## 2. Avaliação

O engine consulta a ACL entre o entitlement e o RBAC, e só quando a checagem tem um `ResourceRef` com `id` (ver [AUTHORIZATION.md](AUTHORIZATION.md)):

1. Reúne as entradas vivas do usuário **e** das roles dele para aquele recurso e ação.
2. Um único `deny` derruba todos os `allow` — deny nunca é sobreponível.
3. Um `allow` autoriza e curto-circuita RBAC e ABAC.
4. Nenhuma entrada = abstenção: segue o RBAC normal.

Consequências práticas:

- ACL `deny` é a forma de tirar acesso de um recurso sensível sem quebrar a role do usuário.
- ACL `allow` é a forma de delegar um recurso específico (um único integration, um único usuário) sem conceder o código global.
- Isolamento de tenant continua acima: ACL de outro tenant não é sequer lida (RLS) nem aplicável (estágio 1).

---

## 3. API

| Método | Rota | Permissão |
|--------|------|-----------|
| `GET` | `/api/v1/acls?resource_type=&resource_id=&subject_id=` | `iam.acl.read` |
| `POST` | `/api/v1/acls` | `iam.acl.grant` |
| `DELETE` | `/api/v1/acls/{acl_id}` | `iam.acl.revoke` |

```json
POST /api/v1/acls
{
  "subject_type": "user",
  "subject_id": "6f1b…",
  "resource_type": "integration",
  "resource_id": "9c2a…",
  "action": "integration.integration.sync",
  "effect": "deny",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

`granted_by` é preenchido com o ator autenticado. Toda concessão/revogação vai para o audit; negativas por ACL aparecem como `AUTHZ_DENIED` com `stage=acl`.

---

## 4. Boas práticas

- **Prefira RBAC.** ACL é exceção; catálogo de exceções grande é sinal de role modelada errado (use bundles).
- **Sempre com validade** quando a exceção for temporária (`expires_at`) — dívida de acesso que se paga sozinha.
- **Deny para bloquear, não para "esconder".** Se o dado nunca deve ser visto por um grupo, isso é modelagem de role/tenant.
- **Resource id estável.** A entrada é por id; recriar o recurso com id novo não herda a ACL.
- Ao adicionar um `resource_type` novo, use exatamente o mesmo `type` que as rotas passam no `ResourceRef`, senão a entrada nunca casa.

Cobertura: [test_acl_provider.py](../backend/tests/unit/modules/iam/test_acl_provider.py) (precedência deny > allow, expiração) e a matriz em [test_authorization_matrix.py](../backend/tests/integration/test_authorization_matrix.py).
