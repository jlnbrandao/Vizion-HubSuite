<script setup lang="ts">
import type { Integration } from '@/layers/integration'
import type { IntegrationSyncResult } from '@/layers/integration'
import IntegrationStatus from './IntegrationStatus.vue'

defineProps<{
  integration: Integration | null
  lastSync?: IntegrationSyncResult | null
  loading?: boolean
}>()

function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}
</script>

<template>
  <div class="integration-sync-status">
    <div v-if="!integration" class="text-grey-6 text-caption">
      Selecione uma integração para ver o resumo de sincronização.
    </div>
    <template v-else>
      <div class="row items-center q-gutter-sm q-mb-sm">
        <div class="text-subtitle2">{{ integration.name }}</div>
        <IntegrationStatus :status="integration.status" dense />
      </div>
      <div class="text-caption q-gutter-xs">
        <div><strong>Última sync:</strong> {{ formatDate(integration.lastSyncAt) }}</div>
        <div v-if="integration.lastError" class="text-negative">
          <strong>Último erro:</strong> {{ integration.lastError }}
        </div>
        <div v-if="loading" class="row items-center q-gutter-xs text-primary">
          <q-spinner size="16px" />
          <span>Sincronizando…</span>
        </div>
        <div v-else-if="lastSync">
          <strong>Último resultado:</strong>
          {{ lastSync.mode }} · {{ lastSync.recordsProcessed }} registros ·
          {{ lastSync.message }}
        </div>
      </div>
    </template>
  </div>
</template>
