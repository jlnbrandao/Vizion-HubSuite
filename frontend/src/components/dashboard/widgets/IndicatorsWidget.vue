<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ data: Record<string, unknown> }>()

const metrics = computed(() => [
  { label: 'Receita no mês', value: formatMoney(props.data.revenue_mtd) },
  { label: 'Pedidos no mês', value: String(props.data.orders_mtd ?? '—') },
  { label: 'Conversão', value: formatPercent(props.data.conversion_rate) },
  { label: 'NPS', value: String(props.data.nps ?? '—') },
])

function formatMoney(value: unknown): string {
  const n = Number(value)
  if (Number.isNaN(n)) return '—'
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
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
  border-left: 3px solid var(--ls-accent);
  padding: 0.55rem 0.85rem;
}

.indicators__metric span {
  display: block;
  color: var(--ls-muted);
  font-size: 0.8rem;
}

.indicators__metric strong {
  font-family: var(--ls-font-display);
  font-size: 1.3rem;
}
</style>
