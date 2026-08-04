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
  border-radius: 14px;
  background: linear-gradient(160deg, rgba(15, 118, 110, 0.08), rgba(245, 158, 11, 0.08));
}

.stats__label {
  display: block;
  text-transform: capitalize;
  color: var(--ls-muted);
  font-size: 0.78rem;
  margin-bottom: 0.35rem;
}

.stats__value {
  font-size: 1.35rem;
  font-family: var(--ls-font-display);
}
</style>
