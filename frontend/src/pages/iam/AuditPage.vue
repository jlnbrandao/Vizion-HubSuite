<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '@/services/api'

interface AuditRow {
  id: string
  action: string
  actor_type: string
  resource_id: string | null
  created_at: string | null
}

const rows = ref<AuditRow[]>([])
const loading = ref(false)
const error = ref('')

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get<AuditRow[]>('/audit-events')
    rows.value = data
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Failed to load audit events'
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <q-page padding>
    <h1 class="text-h5 q-mb-md">Audit trail</h1>
    <q-banner v-if="error" class="bg-negative text-white q-mb-md">{{ error }}</q-banner>
    <q-table
      :rows="rows"
      :loading="loading"
      row-key="id"
      flat
      bordered
      :columns="[
        { name: 'created_at', label: 'When', field: 'created_at' },
        { name: 'action', label: 'Action', field: 'action' },
        { name: 'actor_type', label: 'Actor', field: 'actor_type' },
        { name: 'resource_id', label: 'Resource', field: 'resource_id' },
      ]"
    />
  </q-page>
</template>
