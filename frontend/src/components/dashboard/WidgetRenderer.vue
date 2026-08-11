<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardWidget } from '@/types/api'
import { resolveWidgetComponent } from '@/components/dashboard/widgetRegistry'

const props = defineProps<{ widget: DashboardWidget }>()

const component = computed(() => resolveWidgetComponent(props.widget.widget_type))
</script>

<template>
  <section class="widget-shell">
    <header class="widget-shell__head">
      <h2>{{ widget.title }}</h2>
    </header>
    <component
      :is="component"
      v-if="component"
      :data="widget.data"
    />
    <p
      v-else
      class="widget-shell__fallback"
    >
      Unsupported widget type: {{ widget.widget_type }}
    </p>
  </section>
</template>

<style scoped lang="scss">
.widget-shell {
  background: var(--app-content-background, #ffffff);
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  padding: 1.25rem 1.35rem 1.4rem;
  box-shadow: none;
  min-height: 160px;
}

.widget-shell__head h2 {
  margin: 0 0 1rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}

.widget-shell__fallback {
  margin: 0;
  color: #9ca3af;
}
</style>
