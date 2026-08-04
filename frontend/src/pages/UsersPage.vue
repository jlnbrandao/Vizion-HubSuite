<script setup lang="ts">
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'

const { can } = usePermissions()
</script>

<template>
  <q-page class="placeholder">
    <h1>Usuários</h1>
    <p>
      Área protegida no frontend por
      <code>{{ PermissionCode.USERS_READ }}</code>.
    </p>
    <p v-if="can(PermissionCode.USERS_CREATE)">
      Você também pode criar usuários
      (<code>{{ PermissionCode.USERS_CREATE }}</code>).
    </p>
  </q-page>
</template>

<style scoped lang="scss">
.placeholder {
  padding: 1.75rem;
}

.placeholder h1 {
  margin: 0 0 0.5rem;
  font-family: var(--ls-font-display);
}

.placeholder p {
  color: var(--ls-muted);
}

code {
  background: rgba(15, 118, 110, 0.1);
  padding: 0.1rem 0.35rem;
  border-radius: 6px;
}
</style>
