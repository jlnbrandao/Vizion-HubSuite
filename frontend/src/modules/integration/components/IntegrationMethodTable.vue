<script setup lang="ts">
import type { QTableColumn } from 'quasar'
import type { MethodComparisonRow, RecommendationTier } from '@/layers/integration'

defineProps<{
  rows: MethodComparisonRow[]
}>()

const emit = defineEmits<{
  select: [type: MethodComparisonRow['type']]
}>()

const columns: QTableColumn[] = [
  { name: 'label', label: 'Método', field: 'label', align: 'left', sortable: true },
  { name: 'complexity', label: 'Complexidade', field: 'complexity', align: 'left' },
  {
    name: 'thirdPartyImpact',
    label: 'Impacto no terceiro',
    field: 'thirdPartyImpact',
    align: 'left',
  },
  { name: 'security', label: 'Segurança', field: 'security', align: 'left' },
  { name: 'tier', label: 'Orientação', field: 'tier', align: 'left' },
  { name: 'actions', label: '', field: 'type', align: 'right' },
]

function tierLabel(tier: RecommendationTier): string {
  switch (tier) {
    case 'recommended':
      return 'Recomendado'
    case 'alternative':
      return 'Alternativa'
    case 'not_recommended':
      return 'Não recomendado'
  }
}

function tierColor(tier: RecommendationTier): string {
  switch (tier) {
    case 'recommended':
      return 'positive'
    case 'alternative':
      return 'info'
    case 'not_recommended':
      return 'warning'
  }
}
</script>

<template>
  <q-table
    flat
    bordered
    row-key="type"
    :rows="rows"
    :columns="columns"
    :pagination="{ rowsPerPage: 0 }"
    hide-pagination
    class="integration-method-table"
  >
    <template #body-cell-tier="props">
      <q-td :props="props">
        <q-badge :color="tierColor(props.row.tier)">
          {{ tierLabel(props.row.tier) }}
        </q-badge>
      </q-td>
    </template>
    <template #body-cell-actions="props">
      <q-td :props="props">
        <q-btn
          flat
          dense
          color="primary"
          label="Usar"
          @click="emit('select', props.row.type)"
        />
      </q-td>
    </template>
  </q-table>
</template>
