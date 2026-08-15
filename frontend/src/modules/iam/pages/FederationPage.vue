<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { api, apiErrorMessage } from '@/services/api'

interface IdentityProvider {
  id: string
  name: string
  provider_type: 'oidc' | 'saml' | string
  client_id: string | null
  issuer: string | null
  metadata_url: string | null
  attribute_mapping: Record<string, string>
  enabled: boolean
  has_client_secret: boolean
  created_at: string | null
}

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const providers = ref<IdentityProvider[]>([])
const formOpen = ref(false)
const editing = ref<IdentityProvider | null>(null)

const form = reactive({
  name: '',
  provider_type: 'oidc' as 'oidc' | 'saml',
  client_id: '',
  client_secret: '',
  issuer: '',
  metadata_url: '',
  enabled: true,
})

const typeOptions = [
  { label: 'OIDC (Google, Entra, …)', value: 'oidc' },
  { label: 'SAML 2.0 SP', value: 'saml' },
]

const columns: QTableColumn[] = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'provider_type', label: 'Type', field: 'provider_type', align: 'left', sortable: true },
  { name: 'issuer', label: 'Issuer / metadata', field: 'issuer', align: 'left' },
  { name: 'enabled', label: 'Enabled', field: 'enabled', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
]

const title = computed(() => (editing.value ? 'Edit identity provider' : 'New identity provider'))

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<IdentityProvider[]>('/identity-providers')
    providers.value = data
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to load identity providers'),
    })
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.name = ''
  form.provider_type = 'oidc'
  form.client_id = ''
  form.client_secret = ''
  form.issuer = ''
  form.metadata_url = ''
  form.enabled = true
}

function openCreate() {
  if (!can(PermissionCode.FEDERATION_CREATE)) return
  editing.value = null
  resetForm()
  formOpen.value = true
}

function openEdit(row: IdentityProvider) {
  if (!can(PermissionCode.FEDERATION_UPDATE)) return
  editing.value = row
  form.name = row.name
  form.provider_type = row.provider_type === 'saml' ? 'saml' : 'oidc'
  form.client_id = row.client_id || ''
  form.client_secret = ''
  form.issuer = row.issuer || ''
  form.metadata_url = row.metadata_url || ''
  form.enabled = row.enabled
  formOpen.value = true
}

async function onSubmit() {
  saving.value = true
  try {
    if (editing.value) {
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        client_id: form.client_id.trim() || null,
        issuer: form.issuer.trim() || null,
        metadata_url: form.metadata_url.trim() || null,
        enabled: form.enabled,
      }
      if (form.client_secret.trim()) {
        payload.client_secret = form.client_secret.trim()
      }
      await api.patch(`/identity-providers/${editing.value.id}`, payload)
      $q.notify({ type: 'positive', message: 'Identity provider updated' })
    } else {
      await api.post('/identity-providers', {
        name: form.name.trim(),
        provider_type: form.provider_type,
        client_id: form.client_id.trim() || null,
        client_secret: form.client_secret.trim() || null,
        issuer: form.issuer.trim() || null,
        metadata_url: form.metadata_url.trim() || null,
      })
      $q.notify({ type: 'positive', message: 'Identity provider created' })
    }
    formOpen.value = false
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to save identity provider'),
    })
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(row: IdentityProvider) {
  if (!can(PermissionCode.FEDERATION_UPDATE)) return
  try {
    await api.patch(`/identity-providers/${row.id}`, { enabled: !row.enabled })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to update status'),
    })
  }
}

function confirmDelete(row: IdentityProvider) {
  if (!can(PermissionCode.FEDERATION_DELETE)) return
  $q.dialog({
    title: 'Delete identity provider',
    message: `Remove "${row.name}"? Users will no longer be able to sign in with this IdP.`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void removeProvider(row.id)
  })
}

async function removeProvider(id: string) {
  try {
    await api.delete(`/identity-providers/${id}`)
    $q.notify({ type: 'positive', message: 'Identity provider removed' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to delete identity provider'),
    })
  }
}

function issuerLabel(row: IdentityProvider): string {
  return row.issuer || row.metadata_url || '—'
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
            <h1 class="app-page__title">Federation / SSO</h1>
            <p class="app-page__lead">
              Configure identity providers (OIDC / SAML) for this tenant. Secrets stay on the
              backend and are never returned by the API.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn
              v-if="can(PermissionCode.FEDERATION_CREATE)"
              class="app-page__btn-primary"
              unelevated
              icon="add"
              label="New provider"
              @click="openCreate"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="app-page__card">
      <q-card-section>
        <q-table
          flat
          bordered
          row-key="id"
          :rows="providers"
          :columns="columns"
          :loading="loading"
          :pagination="{ rowsPerPage: 10 }"
        >
          <template #body-cell-provider_type="props">
            <q-td :props="props">
              <q-badge :color="props.row.provider_type === 'saml' ? 'orange' : 'primary'">
                {{ String(props.row.provider_type).toUpperCase() }}
              </q-badge>
            </q-td>
          </template>
          <template #body-cell-issuer="props">
            <q-td :props="props">
              <span class="ellipsis" style="max-width: 28rem; display: inline-block">
                {{ issuerLabel(props.row) }}
              </span>
            </q-td>
          </template>
          <template #body-cell-enabled="props">
            <q-td :props="props" class="text-center">
              <q-toggle
                :model-value="props.row.enabled"
                :disable="!can(PermissionCode.FEDERATION_UPDATE)"
                color="positive"
                @update:model-value="toggleEnabled(props.row)"
              />
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props" class="q-gutter-xs">
              <q-btn
                v-if="can(PermissionCode.FEDERATION_UPDATE)"
                flat
                dense
                round
                icon="edit"
                color="grey-8"
                @click="openEdit(props.row)"
              >
                <q-tooltip>Edit</q-tooltip>
              </q-btn>
              <q-btn
                v-if="can(PermissionCode.FEDERATION_DELETE)"
                flat
                dense
                round
                icon="delete"
                color="negative"
                @click="confirmDelete(props.row)"
              >
                <q-tooltip>Delete</q-tooltip>
              </q-btn>
            </q-td>
          </template>
          <template #no-data>
            <div class="full-width row flex-center text-grey-7 q-gutter-sm q-pa-md">
              <q-icon name="link_off" size="md" />
              <span>No identity providers configured yet.</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <q-dialog v-model="formOpen" persistent>
      <q-card class="app-page__dialog app-page__dialog--wide" style="min-width: min(560px, 96vw)">
        <q-card-section>
          <div class="text-h6">{{ title }}</div>
          <div class="app-page__dialog-sub">
            Tenant-scoped SSO IdP. Client secret is write-only.
          </div>
        </q-card-section>

        <q-card-section class="q-pt-none">
          <q-form class="q-gutter-md" @submit.prevent="onSubmit">
            <q-input
              v-model="form.name"
              label="Name"
              outlined
              dense
              :rules="[(v) => !!String(v).trim() || 'Name is required']"
            />
            <q-select
              v-model="form.provider_type"
              :options="typeOptions"
              label="Provider type"
              outlined
              dense
              emit-value
              map-options
              :disable="Boolean(editing)"
            />
            <q-input
              v-model="form.issuer"
              label="Issuer URL"
              outlined
              dense
              hint="OIDC issuer (e.g. https://login.microsoftonline.com/{tenant}/v2.0)"
            />
            <q-input
              v-model="form.metadata_url"
              label="Metadata / authorize URL"
              outlined
              dense
              hint="Optional well-known or authorize endpoint; SAML metadata URL"
            />
            <q-input
              v-model="form.client_id"
              label="Client ID"
              outlined
              dense
            />
            <q-input
              v-model="form.client_secret"
              type="password"
              label="Client secret (write-only)"
              outlined
              dense
              autocomplete="new-password"
              :hint="
                editing?.has_client_secret
                  ? 'Leave blank to keep the existing secret'
                  : 'Required for confidential OIDC clients'
              "
            />
            <q-toggle
              v-if="editing"
              v-model="form.enabled"
              label="Enabled"
              color="positive"
            />

            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancel" color="grey-8" @click="formOpen = false" />
              <q-btn
                type="submit"
                unelevated
                color="primary"
                :label="editing ? 'Save' : 'Create'"
                :loading="saving"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>
