<script setup lang="ts">
import type { QTableColumn } from 'quasar'
import type { IntegrationLogEntry } from '@/layers/integration'

defineProps<{
  logs: IntegrationLogEntry[]
  loading?: boolean
}>()

const columns: QTableColumn[] = [
  { name: 'createdAt', label: 'Quando', field: 'createdAt', align: 'left', sortable: true },
  { name: 'level', label: 'Nível', field: 'level', align: 'left' },
  { name: 'message', label: 'Mensagem', field: 'message', align: 'left' },
]

function levelColor(level: IntegrationLogEntry['level']): string {
  switch (level) {
    case 'error':
      return 'negative'
    case 'warning':
      return 'warning'
    default:
      return 'info'
  }
}

function formatDate(value: string): string {
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
}
</script>

<template>
  <q-table
    flat
    bordered
    dense
    row-key="id"
    :rows="logs"
    :columns="columns"
    :loading="loading"
    :pagination="{ rowsPerPage: 10 }"
  >
    <template #body-cell-createdAt="props">
      <q-td :props="props">{{ formatDate(props.row.createdAt) }}</q-td>
    </template>
    <template #body-cell-level="props">
      <q-td :props="props">
        <q-badge :color="levelColor(props.row.level)">{{ props.row.level }}</q-badge>
      </q-td>
    </template>
    <template #no-data>
      <div class="full-width row flex-center text-grey-6 q-gutter-sm q-pa-md">
        Nenhum log para esta integração.
      </div>
    </template>
  </q-table>
</template>
