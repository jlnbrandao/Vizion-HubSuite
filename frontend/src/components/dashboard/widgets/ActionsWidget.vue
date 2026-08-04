<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps<{ data: Record<string, unknown> }>()
const router = useRouter()

const actions = computed(() => {
  const raw = props.data.actions ?? props.data.reports
  return Array.isArray(raw)
    ? (raw as Array<{ label?: string; route?: string; id?: string }>)
    : []
})

function go(item: { label?: string; route?: string; id?: string }) {
  if (item.route) {
    void router.push(item.route)
  }
}
</script>

<template>
  <div class="actions">
    <button
      v-for="(item, index) in actions"
      :key="item.id ?? item.route ?? index"
      type="button"
      class="actions__btn"
      @click="go(item)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<style scoped lang="scss">
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.actions__btn {
  border: 1px solid var(--ls-line);
  background: transparent;
  color: var(--ls-accent-deep);
  border-radius: 999px;
  padding: 0.45rem 0.95rem;
  font: inherit;
  cursor: pointer;
  transition: background 160ms ease, transform 160ms ease;
}

.actions__btn:hover {
  background: rgba(15, 118, 110, 0.08);
  transform: translateY(-1px);
}
</style>
