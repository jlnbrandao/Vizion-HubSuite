<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ data: Record<string, unknown> }>()

const queue = computed(() => {
  const raw = props.data.queue
  return Array.isArray(raw) ? (raw as Array<{ id: string; label: string }>) : []
})
</script>

<template>
  <div class="ops">
    <div class="ops__meta">
      <span>Data: {{ data.date }}</span>
      <span>Pendentes: {{ data.pending_tasks }}</span>
      <span>Concluídas: {{ data.completed_tasks }}</span>
    </div>
    <ul class="ops__queue">
      <li
        v-for="item in queue"
        :key="item.id"
      >
        {{ item.label }}
      </li>
    </ul>
  </div>
</template>

<style scoped lang="scss">
.ops__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  color: var(--ls-muted);
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.ops__queue {
  margin: 0;
  padding: 0;
  list-style: none;
  display: grid;
  gap: 0.55rem;
}

.ops__queue li {
  padding: 0.7rem 0.85rem;
  border-radius: 12px;
  background: rgba(15, 118, 110, 0.06);
}
</style>
