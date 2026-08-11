<script setup lang="ts">
defineProps<{ data: Record<string, unknown> }>()
</script>

<template>
  <div class="stats">
    <div
      v-for="(value, key) in data"
      :key="String(key)"
      class="stats__item"
    >
      <span class="stats__label">{{ String(key).replaceAll('_', ' ') }}</span>
      <strong class="stats__value">{{ value }}</strong>
    </div>
  </div>
</template>

<style scoped lang="scss">
.stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.stats__item {
  padding: 0.85rem 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  background: var(--app-content-background, #ffffff);
}

.stats__label {
  display: block;
  text-transform: capitalize;
  color: #9ca3af;
  font-size: 0.78rem;
  margin-bottom: 0.35rem;
}

.stats__value {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--q-primary, #1e40af);
}
</style>
