<script setup lang="ts">
import { computed } from 'vue'
import type { MethodComparisonRow, RecommendationTier } from '@/modules/integration/data'

const props = defineProps<{
  method: MethodComparisonRow
  selected?: boolean
}>()

const emit = defineEmits<{
  select: [type: MethodComparisonRow['type']]
}>()

const tierMeta = computed(() => tierPresentation(props.method.tier))

function tierPresentation(tier: RecommendationTier) {
  switch (tier) {
    case 'recommended':
      return { label: 'Recomendado', color: 'positive' }
    case 'alternative':
      return { label: 'Alternativa', color: 'info' }
    case 'not_recommended':
      return { label: 'Não recomendado', color: 'warning' }
  }
}
</script>

<template>
  <q-card
    flat
    bordered
    class="integration-method-card"
    :class="{ 'integration-method-card--selected': selected }"
    clickable
    @click="emit('select', method.type)"
  >
    <q-card-section class="q-pb-none">
      <div class="row items-start justify-between q-gutter-sm">
        <div class="text-subtitle1 text-weight-medium">{{ method.label }}</div>
        <q-chip dense size="sm" :color="tierMeta.color" text-color="white">
          {{ tierMeta.label }}
        </q-chip>
      </div>
      <div class="text-caption text-grey-7 q-mt-xs">{{ method.description }}</div>
    </q-card-section>
    <q-card-section class="q-pt-sm">
      <div class="row q-col-gutter-sm text-caption">
        <div class="col-12 col-sm-4">
          <div class="text-grey-6">Complexidade</div>
          <div>{{ method.complexity }}</div>
        </div>
        <div class="col-12 col-sm-4">
          <div class="text-grey-6">Impacto no terceiro</div>
          <div>{{ method.thirdPartyImpact }}</div>
        </div>
        <div class="col-12 col-sm-4">
          <div class="text-grey-6">Segurança</div>
          <div>{{ method.security }}</div>
        </div>
      </div>
    </q-card-section>
  </q-card>
</template>

<style scoped>
.integration-method-card {
  border-color: #e5e7eb;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  height: 100%;
}

.integration-method-card:hover {
  border-color: #93c5fd;
}

.integration-method-card--selected {
  border-color: var(--q-primary, #1e40af);
  box-shadow: inset 0 0 0 1px var(--q-primary, #1e40af);
}
</style>
