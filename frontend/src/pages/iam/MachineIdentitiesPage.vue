<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { api, apiErrorMessage } from '@/services/api'

interface ServiceAccount {
  id: string
  name: string
  description: string
  role_ids: string[]
  is_active: boolean
}

interface ApiKeyRow {
  id: string
  name: string
  prefix: string
  scopes: string[]
  service_account_id: string
  created_at: string | null
  last_used_at: string | null
  expires_at: string | null
  revoked_at: string | null
}

const $q = useQuasar()
const { can } = usePermissions()

const tab = ref<'accounts' | 'keys'>('accounts')
const loading = ref(false)
const saving = ref(false)

const accounts = ref<ServiceAccount[]>([])
const keys = ref<ApiKeyRow[]>([])

const accountDialogOpen = ref(false)
const keyDialogOpen = ref(false)
const revealedKey = ref('')

const accountForm = reactive({
  name: '',
  description: '',
})

const keyForm = reactive({
  service_account_id: '',
  name: '',
  scopesText: '',
})

const accountOptions = computed(() =>
  accounts.value.map((a) => ({
    label: a.name,
    value: a.id,
    description: a.description || undefined,
  })),
)

const accountNameById = computed(() => {
  const map = new Map<string, string>()
  for (const a of accounts.value) map.set(a.id, a.name)
  return map
})

const accountColumns: QTableColumn[] = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'is_active', label: 'Active', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
]

const keyColumns: QTableColumn[] = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'prefix', label: 'Prefix', field: 'prefix', align: 'left' },
  {
    name: 'service_account',
    label: 'Service account',
    field: 'service_account_id',
    align: 'left',
  },
  { name: 'status', label: 'Status', field: 'revoked_at', align: 'left' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
]

async function load() {
  loading.value = true
  try {
    const tasks: Promise<void>[] = []
    if (can(PermissionCode.SERVICE_ACCOUNTS_READ)) {
      tasks.push(
        api.get<ServiceAccount[]>('/service-accounts').then(({ data }) => {
          accounts.value = data
        }),
      )
    }
    if (can(PermissionCode.API_KEYS_READ)) {
      tasks.push(
        api.get<ApiKeyRow[]>('/api-keys').then(({ data }) => {
          keys.value = data
        }),
      )
    }
    await Promise.all(tasks)
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to load machine identities'),
    })
  } finally {
    loading.value = false
  }
}

function openCreateAccount() {
  if (!can(PermissionCode.SERVICE_ACCOUNTS_CREATE)) return
  accountForm.name = ''
  accountForm.description = ''
  accountDialogOpen.value = true
}

function openCreateKey(accountId?: string) {
  if (!can(PermissionCode.API_KEYS_CREATE)) return
  if (!accounts.value.length) {
    $q.notify({
      type: 'warning',
      message: 'Create a service account first',
    })
    tab.value = 'accounts'
    return
  }
  keyForm.service_account_id = accountId || accounts.value[0]?.id || ''
  keyForm.name = ''
  keyForm.scopesText = ''
  revealedKey.value = ''
  keyDialogOpen.value = true
}

async function submitAccount() {
  saving.value = true
  try {
    await api.post('/service-accounts', {
      name: accountForm.name.trim(),
      description: accountForm.description.trim(),
      role_ids: [],
    })
    $q.notify({ type: 'positive', message: 'Service account created' })
    accountDialogOpen.value = false
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to create service account'),
    })
  } finally {
    saving.value = false
  }
}

async function submitKey() {
  saving.value = true
  revealedKey.value = ''
  try {
    const scopes = keyForm.scopesText
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    const { data } = await api.post<{
      id: string
      prefix: string
      api_key: string
      name: string
    }>('/api-keys', {
      service_account_id: keyForm.service_account_id,
      name: keyForm.name.trim(),
      scopes,
    })
    revealedKey.value = data.api_key
    $q.notify({ type: 'positive', message: 'API key created — copy it now' })
    await load()
    tab.value = 'keys'
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to create API key'),
    })
  } finally {
    saving.value = false
  }
}

function confirmRevoke(row: ApiKeyRow) {
  if (!can(PermissionCode.API_KEYS_DELETE)) return
  if (row.revoked_at) return
  $q.dialog({
    title: 'Revoke API key',
    message: `Revoke "${row.name}" (${row.prefix}…)? This cannot be undone.`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void revokeKey(row.id)
  })
}

async function revokeKey(id: string) {
  try {
    await api.delete(`/api-keys/${id}`)
    $q.notify({ type: 'positive', message: 'API key revoked' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to revoke API key'),
    })
  }
}

async function copySecret() {
  if (!revealedKey.value) return
  try {
    await navigator.clipboard.writeText(revealedKey.value)
    $q.notify({ type: 'positive', message: 'Copied to clipboard' })
  } catch {
    $q.notify({ type: 'warning', message: 'Could not copy — select and copy manually' })
  }
}

function keyStatus(row: ApiKeyRow): string {
  if (row.revoked_at) return 'Revoked'
  return 'Active'
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
            <h1 class="app-page__title">API keys / Service accounts</h1>
            <p class="app-page__lead">
              Machine identities for M2M access. The full API key secret is shown only once at
              creation.
            </p>
          </div>
          <div class="app-page__actions q-gutter-sm">
            <q-btn
              v-if="can(PermissionCode.SERVICE_ACCOUNTS_CREATE)"
              outline
              color="primary"
              icon="smart_toy"
              label="New service account"
              @click="openCreateAccount"
            />
            <q-btn
              v-if="can(PermissionCode.API_KEYS_CREATE)"
              class="app-page__btn-primary"
              unelevated
              icon="vpn_key"
              label="New API key"
              @click="openCreateKey()"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="app-page__card">
      <q-card-section>
        <q-tabs v-model="tab" dense class="text-primary" active-color="primary" indicator-color="primary">
          <q-tab
            v-if="can(PermissionCode.SERVICE_ACCOUNTS_READ)"
            name="accounts"
            icon="smart_toy"
            label="Service accounts"
          />
          <q-tab
            v-if="can(PermissionCode.API_KEYS_READ)"
            name="keys"
            icon="vpn_key"
            label="API keys"
          />
        </q-tabs>
        <q-separator />

        <q-tab-panels v-model="tab" animated>
          <q-tab-panel name="accounts" class="q-px-none">
            <q-table
              flat
              bordered
              row-key="id"
              :rows="accounts"
              :columns="accountColumns"
              :loading="loading"
              :pagination="{ rowsPerPage: 10 }"
            >
              <template #body-cell-is_active="props">
                <q-td :props="props" class="text-center">
                  <q-badge :color="props.row.is_active ? 'positive' : 'grey'">
                    {{ props.row.is_active ? 'Active' : 'Inactive' }}
                  </q-badge>
                </q-td>
              </template>
              <template #body-cell-actions="props">
                <q-td :props="props">
                  <q-btn
                    v-if="can(PermissionCode.API_KEYS_CREATE)"
                    flat
                    dense
                    round
                    icon="vpn_key"
                    color="primary"
                    @click="openCreateKey(props.row.id)"
                  >
                    <q-tooltip>Create API key</q-tooltip>
                  </q-btn>
                </q-td>
              </template>
              <template #no-data>
                <div class="full-width row flex-center text-grey-7 q-pa-md">
                  No service accounts yet.
                </div>
              </template>
            </q-table>
          </q-tab-panel>

          <q-tab-panel name="keys" class="q-px-none">
            <q-table
              flat
              bordered
              row-key="id"
              :rows="keys"
              :columns="keyColumns"
              :loading="loading"
              :pagination="{ rowsPerPage: 10 }"
            >
              <template #body-cell-service_account="props">
                <q-td :props="props">
                  {{ accountNameById.get(props.row.service_account_id) || props.row.service_account_id.slice(0, 8) }}
                </q-td>
              </template>
              <template #body-cell-status="props">
                <q-td :props="props">
                  <q-badge :color="props.row.revoked_at ? 'negative' : 'positive'">
                    {{ keyStatus(props.row) }}
                  </q-badge>
                </q-td>
              </template>
              <template #body-cell-actions="props">
                <q-td :props="props">
                  <q-btn
                    v-if="can(PermissionCode.API_KEYS_DELETE) && !props.row.revoked_at"
                    flat
                    dense
                    round
                    icon="block"
                    color="negative"
                    @click="confirmRevoke(props.row)"
                  >
                    <q-tooltip>Revoke</q-tooltip>
                  </q-btn>
                </q-td>
              </template>
              <template #no-data>
                <div class="full-width row flex-center text-grey-7 q-pa-md">
                  No API keys yet.
                </div>
              </template>
            </q-table>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>
    </q-card>

    <q-dialog v-model="accountDialogOpen" persistent>
      <q-card class="app-page__dialog" style="min-width: min(480px, 96vw)">
        <q-card-section>
          <div class="text-h6">New service account</div>
          <div class="app-page__dialog-sub">Non-human identity used to issue API keys.</div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form class="q-gutter-md" @submit.prevent="submitAccount">
            <q-input
              v-model="accountForm.name"
              label="Name"
              outlined
              dense
              :rules="[(v) => !!String(v).trim() || 'Required']"
            />
            <q-input
              v-model="accountForm.description"
              label="Description"
              outlined
              dense
              type="textarea"
              autogrow
            />
            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancel" color="grey-8" @click="accountDialogOpen = false" />
              <q-btn type="submit" unelevated color="primary" label="Create" :loading="saving" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>

    <q-dialog v-model="keyDialogOpen" persistent>
      <q-card class="app-page__dialog" style="min-width: min(520px, 96vw)">
        <q-card-section>
          <div class="text-h6">New API key</div>
          <div class="app-page__dialog-sub">
            The secret is shown once. Store it securely (header <code>X-API-Key</code> or Bearer).
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-banner v-if="revealedKey" class="bg-warning text-dark q-mb-md" rounded>
            <div class="text-weight-medium q-mb-xs">API key (copy now)</div>
            <code class="text-break">{{ revealedKey }}</code>
            <template #action>
              <q-btn flat dense label="Copy" color="dark" @click="copySecret" />
            </template>
          </q-banner>

          <q-form v-if="!revealedKey" class="q-gutter-md" @submit.prevent="submitKey">
            <q-select
              v-model="keyForm.service_account_id"
              :options="accountOptions"
              label="Service account"
              outlined
              dense
              emit-value
              map-options
              :rules="[(v) => !!v || 'Required']"
            />
            <q-input
              v-model="keyForm.name"
              label="Key name"
              outlined
              dense
              :rules="[(v) => !!String(v).trim() || 'Required']"
            />
            <q-input
              v-model="keyForm.scopesText"
              label="Scopes (optional, comma-separated)"
              outlined
              dense
              hint="e.g. scim.provision, addresses:read"
            />
            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancel" color="grey-8" @click="keyDialogOpen = false" />
              <q-btn type="submit" unelevated color="primary" label="Create" :loading="saving" />
            </div>
          </q-form>
          <div v-else class="row justify-end">
            <q-btn
              unelevated
              color="primary"
              label="Done"
              @click="keyDialogOpen = false; revealedKey = ''"
            />
          </div>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>
