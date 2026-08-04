/**
 * Widget render registry — maps widget_type → component.
 * Open/Closed: add a type without scattering if/else in the page.
 */
import { defineAsyncComponent, type Component } from 'vue'

const registry: Record<string, Component> = {
  stats: defineAsyncComponent(() => import('@/components/dashboard/widgets/StatsWidget.vue')),
  indicators: defineAsyncComponent(
    () => import('@/components/dashboard/widgets/IndicatorsWidget.vue'),
  ),
  operations: defineAsyncComponent(
    () => import('@/components/dashboard/widgets/OperationsWidget.vue'),
  ),
  profile: defineAsyncComponent(() => import('@/components/dashboard/widgets/ProfileWidget.vue')),
  readonly: defineAsyncComponent(
    () => import('@/components/dashboard/widgets/ReadonlyWidget.vue'),
  ),
  actions: defineAsyncComponent(() => import('@/components/dashboard/widgets/ActionsWidget.vue')),
}

export function resolveWidgetComponent(widgetType: string): Component | null {
  return registry[widgetType] ?? null
}
