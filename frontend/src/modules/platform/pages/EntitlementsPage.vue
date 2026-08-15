<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { apiErrorMessage, servicesApi, tenantsApi } from '@/services/api'
import type { TenantServiceResponse } from '@/types/api'

interface TenantOption {
  label: string
  value: string
}

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const tenantOptions = ref<TenantOption[]>([])
const selectedTenant = ref<string | null>(null)
const services = ref<TenantServiceResponse[]>([])
const editOpen = ref(false)

const form = reactive({
  slug: '',
  name: '',
  isCore: false,
  status: 'active',
  plan: 'standard',
  quotas: '{}',
})

const statusOptions = [
  { label: 'Active — fully available', value: 'active' },
  { label: 'Trial — available, time-boxed', value: 'trial' },
  { label: 'Suspended — blocked, data kept', value: 'suspended' },
  { label: 'Disabled — not contracted', value: 'disabled' },
]

const columns: QTableColumn[] = [
  { name: 'name', label: 'Service', field: 'name', align: 'left', sortable: true },
  { name: 'namespace', label: 'Namespace', field: 'namespace', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left', sortable: true },
  { name: 'plan', label: 'Plan', field: 'plan', align: 'left' },
  { name: 'quotas', label: 'Quotas', field: 'quotas', align: 'left' },
  { name: 'actions', label: '', field: 'slug', align: 'right' },
]

const canManage = computed(() => can(PermissionCode.SERVICES_MANAGE))

function statusColor(row: TenantServiceResponse): string {
  if (row.entitled) return row.status === 'trial' ? 'warning' : 'positive'
  return row.status === 'suspended' ? 'negative' : 'grey-6'
}

async function loadTenants() {
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

async function loadServices() {
  if (!selectedTenant.value) {
    services.value = []
    return
  }
  loading.value = true
  try {
    const { data } = await servicesApi.forTenant(selectedTenant.value)
    services.value = data
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load services') })
  } finally {
    loading.value = false
  }
}

function openEdit(row: TenantServiceResponse) {
  if (!canManage.value) return
  form.slug = row.slug
  form.name = row.name
  form.isCore = row.is_core
  form.status = row.status ?? 'active'
  form.plan = row.plan ?? 'standard'
  form.quotas = JSON.stringify(row.quotas ?? {}, null, 2)
  editOpen.value = true
}

async function submit() {
  let quotas: Record<string, unknown>
  try {
    quotas = JSON.parse(form.quotas || '{}')
  } catch {
    $q.notify({ type: 'negative', message: 'Quotas must be valid JSON' })
    return
  }
  if (!selectedTenant.value) return

  saving.value = true
  try {
    await servicesApi.setForTenant(selectedTenant.value, form.slug, {
      status: form.status,
      plan: form.plan,
      quotas,
    })
    $q.notify({ type: 'positive', message: `${form.name} updated` })
    editOpen.value = false
    await loadServices()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to update service') })
  } finally {
    saving.value = false
  }
}

watch(selectedTenant, () => {
  void loadServices()
})

onMounted(async () => {
  await loadTenants()
  await loadServices()
})
</script>

<template>
  <q-page class="app-page q-pa-md">
    <q-card flat bordered class="app-page__card q-mb-md">
      <q-card-section class="app-page__section">
        <div class="app-page__header">
          <div>
            <h1 class="app-page__title">Service entitlements</h1>
            <p class="app-page__lead">
              Which Hub services each tenant has contracted. A suspended or disabled service is
              refused by the authorization engine before any permission is considered, and
              disappears from that tenant's menu. Core services keep the Hub itself working and
              cannot be turned off.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn outline color="primary" icon="refresh" label="Reload" @click="loadServices" />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="app-page__card">
      <q-card-section>
        <q-select
          v-model="selectedTenant"
          :options="tenantOptions"
          label="Tenant"
          outlined
          dense
          emit-value
          map-options
          style="max-width: 420px"
        />
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-table
          flat
          bordered
          row-key="slug"
          :rows="services"
          :columns="columns"
          :loading="loading"
          :pagination="{ rowsPerPage: 15 }"
        >
          <template #body-cell-name="props">
            <q-td :props="props">
              <div class="row items-center q-gutter-xs">
                <span>{{ props.row.name }}</span>
                <q-badge v-if="props.row.is_core" color="primary" outline>core</q-badge>
              </div>
              <div class="text-caption text-grey-7">{{ props.row.description }}</div>
            </q-td>
          </template>
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="statusColor(props.row)">
                {{ (props.row.status ?? 'not contracted').toUpperCase() }}
              </q-badge>
            </q-td>
          </template>
          <template #body-cell-plan="props">
            <q-td :props="props">{{ props.row.plan ?? '—' }}</q-td>
          </template>
          <template #body-cell-quotas="props">
            <q-td :props="props">
              <code class="text-caption">{{ JSON.stringify(props.row.quotas ?? {}) }}</code>
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="canManage"
                flat
                dense
                round
                icon="tune"
                color="primary"
                @click="openEdit(props.row)"
              >
                <q-tooltip>Edit entitlement</q-tooltip>
              </q-btn>
            </q-td>
          </template>
          <template #no-data>
            <div class="full-width row flex-center text-grey-7 q-gutter-sm q-pa-md">
              <q-icon name="widgets" size="md" />
              <span>No services registered in the catalog.</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <q-dialog v-model="editOpen" persistent>
      <q-card class="app-page__dialog" style="min-width: min(520px, 96vw)">
        <q-card-section>
          <div class="text-h6">{{ form.name }}</div>
          <div class="app-page__dialog-sub">
            {{
              form.isCore
                ? 'Core service: it stays available, but the plan and quotas are yours to set.'
                : 'Changes take effect on the next request.'
            }}
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form class="q-gutter-md" @submit.prevent="submit">
            <q-select
              v-model="form.status"
              :options="statusOptions"
              :disable="form.isCore"
              label="Status"
              outlined
              dense
              emit-value
              map-options
            />
            <q-input v-model="form.plan" label="Plan" outlined dense />
            <q-input
              v-model="form.quotas"
              type="textarea"
              label="Quotas (JSON)"
              hint='e.g. { "requests_per_minute": 600 }'
              autogrow
              outlined
              dense
            />
            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancel" color="grey-8" @click="editOpen = false" />
              <q-btn type="submit" unelevated color="primary" label="Save" :loading="saving" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>
