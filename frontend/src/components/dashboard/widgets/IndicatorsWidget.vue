<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ data: Record<string, unknown> }>()

const metrics = computed(() => [
  { label: 'Revenue MTD', value: formatMoney(props.data.revenue_mtd) },
  { label: 'Orders MTD', value: String(props.data.orders_mtd ?? '—') },
  { label: 'Conversion', value: formatPercent(props.data.conversion_rate) },
  { label: 'NPS', value: String(props.data.nps ?? '—') },
])

function formatMoney(value: unknown): string {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function formatPercent(value: unknown): string {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return `${(n * 100).toFixed(1)}%`
}
</script>

<template>
  <div class="indicators">
    <article
      v-for="metric in metrics"
      :key="metric.label"
      class="indicators__metric"
    >
      <span>{{ metric.label }}</span>
      <strong>{{ metric.value }}</strong>
    </article>
  </div>
</template>

<style scoped lang="scss">
.indicators {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.indicators__metric {
  border-left: 3px solid var(--q-primary, #1e40af);
  padding: 0.55rem 0.85rem;
}

.indicators__metric span {
  display: block;
  color: #9ca3af;
  font-size: 0.8rem;
}

.indicators__metric strong {
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--q-primary, #1e40af);
}
</style>
