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
      Tipo de widget não suportado: {{ widget.widget_type }}
    </p>
  </section>
</template>

<style scoped lang="scss">
.widget-shell {
  background: var(--ls-panel);
  border: 1px solid var(--ls-line);
  border-radius: 18px;
  padding: 1.25rem 1.35rem 1.4rem;
  box-shadow: var(--ls-shadow);
  min-height: 160px;
  animation: rise 420ms ease both;
}

.widget-shell__head h2 {
  margin: 0 0 1rem;
  font-family: var(--ls-font-display);
  font-size: 1.2rem;
  font-weight: 600;
}

.widget-shell__fallback {
  margin: 0;
  color: var(--ls-muted);
}

@keyframes rise {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
