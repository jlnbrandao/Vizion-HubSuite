<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ data: Record<string, unknown> }>()

const allowed = computed(() => {
  const raw = props.data.allowed_actions
  return Array.isArray(raw) ? (raw as string[]) : []
})

const denied = computed(() => {
  const raw = props.data.denied_actions
  return Array.isArray(raw) ? (raw as string[]) : []
})
</script>

<template>
  <div class="readonly">
    <p>{{ data.message }}</p>
    <div class="readonly__tags">
      <span
        v-for="action in allowed"
        :key="`ok-${action}`"
        class="ok"
      >{{ action }}</span>
      <span
        v-for="action in denied"
        :key="`no-${action}`"
        class="no"
      >{{ action }}</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.readonly p {
  margin: 0 0 1rem;
  color: var(--ls-muted);
}

.readonly__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.readonly__tags span {
  border-radius: 999px;
  padding: 0.25rem 0.7rem;
  font-size: 0.78rem;
  text-transform: capitalize;
}

.ok {
  background: rgba(5, 150, 105, 0.12);
  color: #047857;
}

.no {
  background: rgba(220, 38, 38, 0.1);
  color: #b91c1c;
}
</style>
