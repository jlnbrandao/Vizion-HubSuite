<script setup lang="ts">
import type { IntegrationTestResult } from '@/layers/integration'

defineProps<{
  result: IntegrationTestResult | null
  loading?: boolean
}>()
</script>

<template>
  <div class="integration-test-result">
    <div v-if="loading" class="row items-center q-gutter-sm text-grey-7">
      <q-spinner size="20px" color="primary" />
      <span>Testando conexão…</span>
    </div>
    <template v-else-if="result">
      <div class="row items-center q-gutter-sm q-mb-sm">
        <q-icon
          :name="result.success ? 'check_circle' : 'cancel'"
          :color="result.success ? 'positive' : 'negative'"
          size="24px"
        />
        <div class="text-subtitle1">{{ result.message }}</div>
      </div>
      <div v-if="result.success" class="q-gutter-xs">
        <div v-if="result.server"><strong>Servidor:</strong> {{ result.server }}</div>
        <div v-if="result.durationMs != null">
          <strong>Tempo:</strong> {{ result.durationMs }} ms
        </div>
        <div v-if="result.authentication">
          <strong>Autenticação:</strong> {{ result.authentication }}
        </div>
        <div v-if="result.permission">
          <strong>Permissão:</strong> {{ result.permission }}
        </div>
      </div>
      <div v-else class="text-negative">
        {{ result.errorDetail || 'Não foi possível autenticar no servidor terceiro.' }}
      </div>
    </template>
    <div v-else class="text-grey-6 text-caption">
      Execute um teste para ver o resultado aqui.
    </div>
  </div>
</template>
