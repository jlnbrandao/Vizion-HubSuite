<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { api, apiErrorMessage, rolesApi, usersApi } from '@/services/api'

interface AclEntry {
  id: string
  subject_type: 'user' | 'role'
  subject_id: string
  resource_type: string
  resource_id: string
  action: string
  effect: 'allow' | 'deny'
  granted_by: string | null
  expires_at: string | null
  created_at: string | null
}

interface SubjectOption {
  label: string
  value: string
}

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const entries = ref<AclEntry[]>([])
const formOpen = ref(false)
const userOptions = ref<SubjectOption[]>([])
const roleOptions = ref<SubjectOption[]>([])

const filters = reactive({ resourceType: '', resourceId: '' })

const form = reactive({
  subject_type: 'user' as 'user' | 'role',
  subject_id: '',
  resource_type: '',
  resource_id: '',
  action: '',
  effect: 'allow' as 'allow' | 'deny',
})

const subjectTypeOptions = [
  { label: 'User', value: 'user' },
  { label: 'Role', value: 'role' },
]

const effectOptions = [
  { label: 'Allow (grant this resource only)', value: 'allow' },
  { label: 'Deny (block, overrides roles)', value: 'deny' },
]

const columns: QTableColumn[] = [
  { name: 'effect', label: 'Effect', field: 'effect', align: 'left', sortable: true },
  { name: 'subject', label: 'Subject', field: 'subject_id', align: 'left' },
  { name: 'resource', label: 'Resource', field: 'resource_type', align: 'left' },
  { name: 'action', label: 'Action', field: 'action', align: 'left', sortable: true },
  { name: 'expires_at', label: 'Expires', field: 'expires_at', align: 'left' },
  { name: 'actions', label: '', field: 'id', align: 'right' },
]

const subjectOptions = computed(() =>
  form.subject_type === 'user' ? userOptions.value : roleOptions.value,
)

const subjectNames = computed(() => {
  const map = new Map<string, string>()
  for (const option of [...userOptions.value, ...roleOptions.value]) {
    map.set(option.value, option.label)
  }
  return map
})

function subjectLabel(row: AclEntry): string {
  return subjectNames.value.get(row.subject_id) ?? row.subject_id
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<AclEntry[]>('/acls', {
      params: {
        resource_type: filters.resourceType.trim() || undefined,
        resource_id: filters.resourceId.trim() || undefined,
      },
    })
    entries.value = data
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load ACL entries') })
  } finally {
    loading.value = false
  }
}

async function loadSubjects() {
  if (can(PermissionCode.USERS_READ)) {
    try {
      const { data } = await usersApi.list()
      userOptions.value = data.map((user) => ({
        label: `${user.full_name} (${user.email})`,
        value: user.id,
      }))
    } catch {
      userOptions.value = []
    }
  }
  if (can(PermissionCode.ROLES_READ)) {
    try {
      const { data } = await rolesApi.list()
      roleOptions.value = data.map((role) => ({ label: role.name, value: role.id }))
    } catch {
      roleOptions.value = []
    }
  }
}

function openCreate() {
  if (!can(PermissionCode.ACL_GRANT)) return
  form.subject_type = 'user'
  form.subject_id = ''
  form.resource_type = ''
  form.resource_id = ''
  form.action = ''
  form.effect = 'allow'
  formOpen.value = true
}

async function onSubmit() {
  saving.value = true
  try {
    await api.post('/acls', {
      subject_type: form.subject_type,
      subject_id: form.subject_id,
      resource_type: form.resource_type.trim(),
      resource_id: form.resource_id.trim(),
      action: form.action.trim(),
      effect: form.effect,
    })
    $q.notify({ type: 'positive', message: 'ACL entry saved' })
    formOpen.value = false
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to save ACL entry') })
  } finally {
    saving.value = false
  }
}

function confirmRevoke(row: AclEntry) {
  if (!can(PermissionCode.ACL_REVOKE)) return
  $q.dialog({
    title: 'Revoke ACL entry',
    message: `Remove the ${row.effect} entry for ${row.resource_type}/${row.resource_id}?`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void revoke(row.id)
  })
}

async function revoke(id: string) {
  try {
    await api.delete(`/acls/${id}`)
    $q.notify({ type: 'positive', message: 'ACL entry revoked' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to revoke ACL entry') })
  }
}

onMounted(() => {
  void load()
  void loadSubjects()
})
</script>

<template>
  <q-page class="app-page q-pa-md">
    <q-card flat bordered class="app-page__card q-mb-md">
      <q-card-section class="app-page__section">
        <div class="app-page__header">
          <div>
            <h1 class="app-page__title">Resource ACLs</h1>
            <p class="app-page__lead">
              Exceptions for a single resource. A deny entry overrides any role permission; an
              allow entry grants access to that one resource without a global permission. Tenant
              isolation always applies.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn
              v-if="can(PermissionCode.ACL_GRANT)"
              class="app-page__btn-primary"
              unelevated
              icon="add"
              label="New entry"
              @click="openCreate"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="app-page__card">
      <q-card-section class="row q-col-gutter-md items-end">
        <q-input
          v-model="filters.resourceType"
          class="col-12 col-sm-4"
          label="Filter by resource type"
          outlined
          dense
          clearable
          @keyup.enter="load"
        />
        <q-input
          v-model="filters.resourceId"
          class="col-12 col-sm-4"
          label="Filter by resource id"
          outlined
          dense
          clearable
          @keyup.enter="load"
        />
        <div class="col-12 col-sm-4">
          <q-btn outline color="primary" icon="search" label="Apply" @click="load" />
        </div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <q-table
          flat
          bordered
          row-key="id"
          :rows="entries"
          :columns="columns"
          :loading="loading"
          :pagination="{ rowsPerPage: 10 }"
        >
          <template #body-cell-effect="props">
            <q-td :props="props">
              <q-badge :color="props.row.effect === 'deny' ? 'negative' : 'positive'">
                {{ String(props.row.effect).toUpperCase() }}
              </q-badge>
            </q-td>
          </template>
          <template #body-cell-subject="props">
            <q-td :props="props">
              <div>{{ subjectLabel(props.row) }}</div>
              <div class="text-caption text-grey-7">{{ props.row.subject_type }}</div>
            </q-td>
          </template>
          <template #body-cell-resource="props">
            <q-td :props="props">
              <div>{{ props.row.resource_type }}</div>
              <div class="text-caption text-grey-7">{{ props.row.resource_id }}</div>
            </q-td>
          </template>
          <template #body-cell-expires_at="props">
            <q-td :props="props">
              {{ props.row.expires_at ? new Date(props.row.expires_at).toLocaleString() : 'never' }}
            </q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="can(PermissionCode.ACL_REVOKE)"
                flat
                dense
                round
                icon="delete"
                color="negative"
                @click="confirmRevoke(props.row)"
              >
                <q-tooltip>Revoke</q-tooltip>
              </q-btn>
            </q-td>
          </template>
          <template #no-data>
            <div class="full-width row flex-center text-grey-7 q-gutter-sm q-pa-md">
              <q-icon name="rule" size="md" />
              <span>No ACL entries — access is decided by roles alone.</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <q-dialog v-model="formOpen" persistent>
      <q-card class="app-page__dialog" style="min-width: min(520px, 96vw)">
        <q-card-section>
          <div class="text-h6">New ACL entry</div>
          <div class="app-page__dialog-sub">
            Applies to one subject, one resource and one action.
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form class="q-gutter-md" @submit.prevent="onSubmit">
            <q-select
              v-model="form.subject_type"
              :options="subjectTypeOptions"
              label="Subject type"
              outlined
              dense
              emit-value
              map-options
              @update:model-value="form.subject_id = ''"
            />
            <q-select
              v-model="form.subject_id"
              :options="subjectOptions"
              label="Subject"
              outlined
              dense
              emit-value
              map-options
              use-input
              input-debounce="0"
              :rules="[(v) => !!v || 'Subject is required']"
            />
            <q-input
              v-model="form.resource_type"
              label="Resource type"
              hint="e.g. vehicle, integration, report"
              outlined
              dense
              :rules="[(v) => !!String(v).trim() || 'Resource type is required']"
            />
            <q-input
              v-model="form.resource_id"
              label="Resource id"
              outlined
              dense
              :rules="[(v) => !!String(v).trim() || 'Resource id is required']"
            />
            <q-input
              v-model="form.action"
              label="Action (permission code)"
              hint="e.g. integration.update"
              outlined
              dense
              :rules="[(v) => !!String(v).trim() || 'Action is required']"
            />
            <q-select
              v-model="form.effect"
              :options="effectOptions"
              label="Effect"
              outlined
              dense
              emit-value
              map-options
            />
            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancel" color="grey-8" @click="formOpen = false" />
              <q-btn type="submit" unelevated color="primary" label="Save" :loading="saving" />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>
