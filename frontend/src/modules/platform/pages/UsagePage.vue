<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { apiErrorMessage, tenantsApi, usageApi } from '@/services/api'
import type { UsageQuery, UsageRecordResponse, UsageReportResponse } from '@/types/api'

interface TenantOption {
  label: string
  value: string
}

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const report = ref<UsageReportResponse | null>(null)
const tenantOptions = ref<TenantOption[]>([])
const selectedTenant = ref<string | null>(null)
const granularity = ref<'day' | 'month'>('day')
const windowDays = ref(30)

const canReadAll = computed(() => can(PermissionCode.USAGE_READ_ALL))

const windowOptions = [
  { label: 'Last 7 days', value: 7 },
  { label: 'Last 30 days', value: 30 },
  { label: 'Last 90 days', value: 90 },
  { label: 'Last 12 months', value: 365 },
]

const granularityOptions = [
  { label: 'Daily', value: 'day' },
  { label: 'Monthly', value: 'month' },
]

const columns: QTableColumn<UsageRecordResponse>[] = [
  {
    name: 'period_start',
    label: 'Period',
    field: 'period_start',
    align: 'left',
    sortable: true,
    format: (value: string) => formatPeriod(value),
  },
  { name: 'service', label: 'Service', field: 'service', align: 'left', sortable: true },
  { name: 'metric', label: 'Metric', field: 'metric', align: 'left', sortable: true },
  {
    name: 'quantity',
    label: 'Quantity',
    field: 'quantity',
    align: 'right',
    sortable: true,
    format: (value: number) => value.toLocaleString(),
  },
]

const totals = computed(() =>
  Object.entries(report.value?.totals_by_service ?? {}).sort((a, b) => b[1] - a[1]),
)

const grandTotal = computed(() => totals.value.reduce((sum, [, value]) => sum + value, 0))

function formatPeriod(value: string): string {
  const date = new Date(value)
  return granularity.value === 'month'
    ? date.toLocaleDateString(undefined, { year: 'numeric', month: 'long' })
    : date.toLocaleDateString()
}

function formatRange(value: string | undefined): string {
  return value ? new Date(value).toLocaleDateString() : '—'
}

function query(): UsageQuery {
  const since = new Date()
  since.setDate(since.getDate() - windowDays.value)
  return { since: since.toISOString(), granularity: granularity.value }
}

async function loadTenants() {
  if (!canReadAll.value) return
  try {
    const { data } = await tenantsApi.list()
    tenantOptions.value = data.map((tenant) => ({
      label: `${tenant.name} (${tenant.slug})`,
      value: tenant.id,
    }))
    selectedTenant.value = tenantOptions.value[0]?.value ?? null
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load tenants') })
  }
}

async function load() {
  loading.value = true
  try {
    const { data } =
      canReadAll.value && selectedTenant.value
        ? await usageApi.forTenant(selectedTenant.value, query())
        : await usageApi.mine(query())
    report.value = data
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load usage') })
  } finally {
    loading.value = false
  }
}

watch([selectedTenant, granularity, windowDays], () => {
  void load()
})

onMounted(async () => {
  await loadTenants()
  await load()
})
</script>

<template>
  <q-page class="app-page q-pa-md">
    <q-card flat bordered class="app-page__card q-mb-md">
      <q-card-section class="app-page__section">
        <div class="app-page__header">
          <div>
            <h1 class="app-page__title">Usage</h1>
            <p class="app-page__lead">
              Metered consumption per service and metric. Counters are incremented when a metered
              operation passes its quota check, so what you see here is what a plan is billed for.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn outline color="primary" icon="refresh" label="Reload" @click="load" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="app-page__card q-mb-md">
      <q-card-section class="row q-col-gutter-md items-end">
        <div v-if="canReadAll" class="col-12 col-md-4">
          <q-select
            v-model="selectedTenant"
            :options="tenantOptions"
            label="Tenant"
            outlined
            dense
            emit-value
            map-options
          />
        </div>
        <div class="col-12 col-sm-6 col-md-4">
          <q-select
            v-model="windowDays"
            :options="windowOptions"
            label="Window"
            outlined
            dense
            emit-value
            map-options
          />
        </div>
        <div class="col-12 col-sm-6 col-md-4">
          <q-select
            v-model="granularity"
            :options="granularityOptions"
            label="Granularity"
            outlined
            dense
            emit-value
            map-options
          />
        </div>
      </q-card-section>
    </q-card>

    <div class="row q-col-gutter-md q-mb-md">
      <div class="col-12 col-sm-6 col-md-3">
        <q-card flat bordered class="app-page__card">
          <q-card-section>
            <div class="text-caption text-grey-7">Total units</div>
            <div class="text-h5">{{ grandTotal.toLocaleString() }}</div>
            <div class="text-caption text-grey-7">
              {{ formatRange(report?.since) }} — {{ formatRange(report?.until) }}
            </div>
          </q-card-section>
        </q-card>
      </div>
      <div v-for="[service, total] of totals" :key="service" class="col-12 col-sm-6 col-md-3">
        <q-card flat bordered class="app-page__card">
          <q-card-section>
            <div class="text-caption text-grey-7">{{ service }}</div>
            <div class="text-h5">{{ total.toLocaleString() }}</div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-card flat bordered class="app-page__card">
      <q-card-section class="q-pt-none">
        <q-table
          flat
          bordered
          row-key="period_start"
          :rows="report?.records ?? []"
          :columns="columns"
          :loading="loading"
          :pagination="{ rowsPerPage: 25, sortBy: 'period_start', descending: true }"
        >
          <template #no-data>
            <div class="full-width row flex-center text-grey-7 q-gutter-sm q-pa-md">
              <q-icon name="query_stats" size="md" />
              <span>No usage recorded in this period.</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>
