<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { apiErrorMessage, productsApi, tenantsApi } from '@/services/api'
import type {
  HubLocationResponse,
  ProductInstanceResponse,
  ProductSlug,
  TenantResponse,
} from '@/types/api'

const $q = useQuasar()
const { can } = usePermissions()
const canManage = computed(() => can(PermissionCode.PRODUCTS_MANAGE))

const loading = ref(false)
const hub = ref<HubLocationResponse | null>(null)
const instances = ref<ProductInstanceResponse[]>([])
const tenants = ref<TenantResponse[]>([])
const createOpen = ref(false)
const editOpen = ref(false)
const bindOpen = ref(false)
const selected = ref<ProductInstanceResponse | null>(null)
const bindTenantId = ref<string | null>(null)

const environmentOptions = [
  { label: 'Local Docker', value: 'local_docker' },
  { label: 'Local VPS', value: 'local_vps' },
  { label: 'Remote Docker', value: 'remote_docker' },
  { label: 'Remote VPS', value: 'remote_vps' },
  { label: 'Cloud', value: 'cloud' },
]

const environmentColor: Record<string, string> = {
  local_docker: 'teal',
  local_vps: 'primary',
  remote_docker: 'indigo',
  remote_vps: 'deep-orange',
  cloud: 'purple',
  in_process: 'blue-grey',
}

const productSlugOptions = ref<{ label: string; value: ProductSlug }[]>([
  { label: 'Tracking', value: 'tracking' },
  { label: 'IoT', value: 'iot' },
  { label: 'SNMP', value: 'snmp' },
  { label: 'GIS', value: 'gis' },
  { label: 'Lanstar', value: 'lanstar' },
])

const form = reactive({
  slug: 'tracking' as ProductSlug,
  name: '',
  environment: 'local_docker',
  host: 'localhost',
  api_port: 8100,
  ui_host: 'localhost',
  ui_port: 9100,
  scheme: 'http',
  client_id: 'tracking-local',
  client_secret: 'tracking-client-secret',
  notes: '',
})

const columns: QTableColumn[] = [
  { name: 'name', label: 'Instance', field: 'name', align: 'left', sortable: true },
  { name: 'slug', label: 'Service', field: 'slug', align: 'left' },
  { name: 'environment', label: 'Where', field: 'environment', align: 'left' },
  { name: 'endpoint', label: 'Host / ports', field: 'host', align: 'left' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'tenants', label: 'Tenants', field: 'id', align: 'left' },
  { name: 'heartbeat', label: 'Last seen', field: 'last_heartbeat_at', align: 'left' },
  { name: 'actions', label: '', field: 'id', align: 'right' },
]

function envLabel(value: string): string {
  return environmentOptions.find((item) => item.value === value)?.label ?? value
}

function formatSeen(value: string | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleString()
}

function endpoint(row: ProductInstanceResponse): string {
  const api = row.api_port ? `${row.host}:${row.api_port}` : row.host || row.base_url
  const ui =
    row.ui_port != null ? `${row.ui_host || row.host}:${row.ui_port}` : row.ui_url
  return ui ? `${api}  ·  UI ${ui}` : api
}

async function load() {
  loading.value = true
  try {
    const [{ data: topology }, { data: tenantRows }] = await Promise.all([
      productsApi.topology(),
      tenantsApi.list(),
    ])
    hub.value = topology.hub
    instances.value = topology.instances
    if (topology.product_options?.length) {
      productSlugOptions.value = topology.product_options.map((item) => ({
        label: item.name,
        value: item.slug as ProductSlug,
      }))
    }
    tenants.value = tenantRows
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load deployments') })
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.slug = 'tracking'
  form.name = ''
  form.environment = 'local_docker'
  form.host = 'localhost'
  form.api_port = 8100
  form.ui_host = 'localhost'
  form.ui_port = 9100
  form.scheme = 'http'
  form.client_id = 'tracking-local'
  form.client_secret = 'tracking-client-secret'
  form.notes = ''
}

function payload() {
  return {
    slug: form.slug,
    name: form.name,
    environment: form.environment,
    host: form.host,
    api_port: Number(form.api_port),
    ui_host: form.ui_host || null,
    ui_port: form.ui_port ? Number(form.ui_port) : null,
    scheme: form.scheme,
    client_id: form.client_id,
    client_secret: form.client_secret,
    notes: form.notes,
  }
}

async function create() {
  try {
    await productsApi.create(payload())
    createOpen.value = false
    $q.notify({ type: 'positive', message: 'Deployment registered' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to register deployment') })
  }
}

function openEdit(row: ProductInstanceResponse) {
  selected.value = row
  form.slug = row.slug as ProductSlug
  form.name = row.name
  form.environment = row.environment
  form.host = row.host
  form.api_port = row.api_port ?? 8000
  form.ui_host = row.ui_host ?? ''
  form.ui_port = row.ui_port ?? 0
  form.scheme = row.scheme || 'http'
  form.client_id = row.client_id
  form.client_secret = ''
  form.notes = row.notes
  editOpen.value = true
}

async function saveEdit() {
  if (!selected.value) return
  try {
    await productsApi.update(selected.value.id, {
      name: form.name,
      environment: form.environment,
      host: form.host,
      api_port: Number(form.api_port),
      ui_host: form.ui_host || null,
      ui_port: form.ui_port ? Number(form.ui_port) : null,
      scheme: form.scheme,
      notes: form.notes,
    })
    editOpen.value = false
    $q.notify({ type: 'positive', message: 'Deployment updated' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to update deployment') })
  }
}

async function probe(row: ProductInstanceResponse) {
  try {
    const { data } = await productsApi.probe(row.id)
    $q.notify({
      type: data.ok ? 'positive' : 'warning',
      message: data.ok ? `Ready — ${JSON.stringify(data.version)}` : data.error || 'Unreachable',
    })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Probe failed') })
  }
}

function openBind(row: ProductInstanceResponse) {
  selected.value = row
  bindTenantId.value = tenants.value[0]?.id ?? null
  bindOpen.value = true
}

async function bind() {
  if (!selected.value || !bindTenantId.value) return
  try {
    await productsApi.bind(selected.value.id, bindTenantId.value)
    bindOpen.value = false
    $q.notify({ type: 'positive', message: 'Tenant bound to this deployment' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Bind failed') })
  }
}

async function deactivate(row: ProductInstanceResponse) {
  try {
    await productsApi.deactivate(row.id)
    $q.notify({ type: 'warning', message: 'Deployment disabled' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Disable failed') })
  }
}

function openUi(url: string | null | undefined) {
  if (url) window.open(url, '_blank', 'noopener')
}

onMounted(() => {
  void load()
})
</script>

<template>
  <q-page class="app-page q-pa-md">
    <q-card flat bordered class="app-page__card q-mb-md">
      <q-card-section class="app-page__section">
        <div class="app-page__header">
          <div>
            <h1 class="app-page__title">Deployments</h1>
            <p class="app-page__lead">
              Where each service is running — local or remote, Docker or VPS — with host, ports and
              the tenants served by that instance. Entitlements (who contracted the service) stay on
              Service entitlements; this page is the runtime topology.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn outline color="primary" icon="refresh" label="Reload" @click="load" />
            <q-btn
              v-if="canManage"
              unelevated
              color="primary"
              icon="add"
              label="Register instance"
              @click="resetForm(); createOpen = true"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card v-if="hub" flat bordered class="app-page__card q-mb-md">
      <q-card-section>
        <div class="row items-center q-gutter-sm">
          <div class="text-h6">{{ hub.name }} (Platform Core)</div>
          <q-badge :color="environmentColor[hub.environment] || 'grey'" outline>
            {{ envLabel(hub.environment) }}
          </q-badge>
          <q-badge color="blue-grey" outline>{{ hub.runtime }}</q-badge>
        </div>
        <div class="text-body2 q-mt-sm">
          <strong>Host</strong> {{ hub.host }}
          · <strong>API</strong> {{ hub.api_port }}
          · <strong>UI</strong> {{ hub.ui_port }}
        </div>
        <div class="text-caption text-grey-7 q-mt-xs">
          {{ hub.api_url }} · UI {{ hub.ui_url }}
        </div>
        <div class="q-mt-sm q-gutter-xs">
          <q-chip
            v-for="slug in hub.services"
            :key="slug"
            dense
            outline
            color="primary"
            :label="slug"
          />
        </div>
        <div v-if="hub.notes" class="text-caption q-mt-sm">{{ hub.notes }}</div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="app-page__card">
      <q-table
        flat
        :rows="instances"
        :columns="columns"
        row-key="id"
        :loading="loading"
        :pagination="{ rowsPerPage: 15 }"
      >
        <template #body-cell-name="props">
          <q-td :props="props">
            <div>{{ props.row.name }}</div>
            <div class="text-caption text-grey-7">{{ props.row.version || 'version unknown' }}</div>
          </q-td>
        </template>
        <template #body-cell-environment="props">
          <q-td :props="props">
            <q-badge :color="environmentColor[props.row.environment] || 'grey'">
              {{ envLabel(props.row.environment) }}
            </q-badge>
          </q-td>
        </template>
        <template #body-cell-endpoint="props">
          <q-td :props="props">
            <div>{{ endpoint(props.row) }}</div>
            <div class="text-caption text-grey-7">{{ props.row.scheme }} · {{ props.row.base_url }}</div>
          </q-td>
        </template>
        <template #body-cell-status="props">
          <q-td :props="props">
            <q-badge :color="props.row.status === 'online' ? 'positive' : props.row.status === 'disabled' ? 'grey' : 'warning'">
              {{ props.row.status }}
            </q-badge>
          </q-td>
        </template>
        <template #body-cell-tenants="props">
          <q-td :props="props">
            <span v-if="!props.row.bindings?.length" class="text-grey-6">none bound</span>
            <q-chip
              v-for="binding in props.row.bindings"
              :key="binding.tenant_id"
              dense
              size="sm"
              :label="binding.tenant_slug || binding.tenant_id"
            />
          </q-td>
        </template>
        <template #body-cell-heartbeat="props">
          <q-td :props="props">{{ formatSeen(props.row.last_heartbeat_at) }}</q-td>
        </template>
        <template #body-cell-actions="props">
          <q-td :props="props">
            <q-btn v-if="canManage" flat dense icon="monitor_heart" @click="probe(props.row)">
              <q-tooltip>Probe /ready</q-tooltip>
            </q-btn>
            <q-btn v-if="canManage" flat dense icon="edit" @click="openEdit(props.row)" />
            <q-btn v-if="canManage" flat dense icon="link" @click="openBind(props.row)">
              <q-tooltip>Bind tenant</q-tooltip>
            </q-btn>
            <q-btn flat dense icon="open_in_new" :disable="!props.row.ui_url" @click="openUi(props.row.ui_url)" />
            <q-btn
              v-if="canManage && props.row.status !== 'disabled'"
              flat
              dense
              icon="block"
              @click="deactivate(props.row)"
            />
          </q-td>
        </template>
        <template #no-data>
          <div class="full-width row flex-center text-grey-7 q-gutter-sm q-pa-md">
            <q-icon name="dns" size="md" />
            <span>No remote product instances yet. Hub modules above run in-process.</span>
          </div>
        </template>
      </q-table>
    </q-card>

    <q-dialog v-model="createOpen">
      <q-card class="app-page__dialog" style="min-width: min(560px, 96vw)">
        <q-card-section class="text-h6">Register a product instance</q-card-section>
        <q-card-section class="q-pt-none q-gutter-sm">
          <q-select
            v-model="form.slug"
            :options="productSlugOptions"
            emit-value
            map-options
            label="Product"
            outlined
            dense
          />
          <q-input v-model="form.name" label="Name" outlined dense />
          <q-select
            v-model="form.environment"
            :options="environmentOptions"
            emit-value
            map-options
            label="Environment"
            outlined
            dense
          />
          <div class="row q-gutter-sm">
            <q-select v-model="form.scheme" :options="['http', 'https']" label="Scheme" outlined dense class="col-3" />
            <q-input v-model="form.host" label="Host / IP" outlined dense class="col" />
          </div>
          <div class="row q-gutter-sm">
            <q-input v-model.number="form.api_port" type="number" label="API port" outlined dense class="col" />
            <q-input v-model="form.ui_host" label="UI host" outlined dense class="col" />
            <q-input v-model.number="form.ui_port" type="number" label="UI port" outlined dense class="col" />
          </div>
          <q-input v-model="form.notes" type="textarea" autogrow label="Notes" hint="VPS name, compose project, region…" outlined dense />
          <q-input v-model="form.client_id" label="Client ID" outlined dense />
          <q-input v-model="form.client_secret" type="password" label="Client secret" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" unelevated label="Save" @click="create" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="editOpen">
      <q-card class="app-page__dialog" style="min-width: min(560px, 96vw)">
        <q-card-section class="text-h6">Edit deployment</q-card-section>
        <q-card-section class="q-pt-none q-gutter-sm">
          <q-input v-model="form.name" label="Name" outlined dense />
          <q-select
            v-model="form.environment"
            :options="environmentOptions"
            emit-value
            map-options
            label="Environment"
            outlined
            dense
          />
          <div class="row q-gutter-sm">
            <q-select v-model="form.scheme" :options="['http', 'https']" label="Scheme" outlined dense class="col-3" />
            <q-input v-model="form.host" label="Host / IP" outlined dense class="col" />
          </div>
          <div class="row q-gutter-sm">
            <q-input v-model.number="form.api_port" type="number" label="API port" outlined dense class="col" />
            <q-input v-model="form.ui_host" label="UI host" outlined dense class="col" />
            <q-input v-model.number="form.ui_port" type="number" label="UI port" outlined dense class="col" />
          </div>
          <q-input v-model="form.notes" type="textarea" autogrow label="Notes" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" unelevated label="Save" @click="saveEdit" />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="bindOpen">
      <q-card style="min-width: 420px">
        <q-card-section class="text-h6">Bind tenant</q-card-section>
        <q-card-section>
          <q-select
            v-model="bindTenantId"
            :options="tenants.map((t) => ({ label: `${t.name} (${t.slug})`, value: t.id }))"
            emit-value
            map-options
            label="Tenant"
            outlined
            dense
          />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn color="primary" unelevated label="Bind" @click="bind" />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>
