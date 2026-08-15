<script setup lang="ts">
import { computed } from 'vue'
import type { IntegrationStatus } from '@/modules/integration/data'

const props = defineProps<{
  status: IntegrationStatus
  dense?: boolean
}>()

const meta = computed(() => {
  switch (props.status) {
    case 'ACTIVE':
      return { label: 'Ativa', color: 'positive' }
    case 'INACTIVE':
      return { label: 'Inativa', color: 'grey' }
    case 'ERROR':
      return { label: 'Erro', color: 'negative' }
    case 'TESTING':
      return { label: 'Testando', color: 'info' }
    case 'SYNCING':
      return { label: 'Sincronizando', color: 'primary' }
    case 'NEVER_SYNCED':
      return { label: 'Nunca sincronizada', color: 'warning' }
    default:
      return { label: props.status, color: 'grey' }
  }
})
</script>

<template>
  <q-badge :color="meta.color" :outline="dense" :class="{ 'text-caption': dense }">
    {{ meta.label }}
  </q-badge>
</template>
