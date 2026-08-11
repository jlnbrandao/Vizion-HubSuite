<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionAction, PermissionCode } from '@/constants/permissions'
import { apiErrorMessage, permissionsApi } from '@/services/api'
import type { PermissionResponse } from '@/types/api'

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const permissions = ref<PermissionResponse[]>([])

const filterResource = ref<string | null>(null)
const filterAction = ref<string | null>(null)

const createOpen = ref(false)
const editOpen = ref(false)
const selected = ref<PermissionResponse | null>(null)

const createForm = reactive({
  resource: '',
  action: '' as string | null,
  name: '',
  description: '',
})

const editForm = reactive({
  name: '',
  description: '',
  is_active: true,
})

const columns: QTableColumn[] = [
  { name: 'code', label: 'Code', field: 'code', align: 'left', sortable: true },
  { name: 'resource', label: 'Resource', field: 'resource', align: 'left', sortable: true },
  { name: 'action', label: 'Action', field: 'action', align: 'left', sortable: true },
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'is_active', label: 'Active', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
]

const predefinedActions = Object.values(PermissionAction).slice().sort()

const resourceOptions = computed(() => {
  const values = new Set(permissions.value.map((p) => p.resource))
  return [...values].sort()
})

const filterActionOptions = computed(() => {
  const values = new Set<string>([
    ...predefinedActions,
    ...permissions.value.map((p) => p.action),
  ])
  return [...values].sort()
})

const generatedCode = computed(() => {
  const resource = createForm.resource.trim().toLowerCase()
  const action = (createForm.action ?? '').trim().toLowerCase()
  if (!resource || !action) return ''
  return `${resource}.${action}`
})

const filteredPermissions = computed(() => {
  return permissions.value.filter((permission) => {
    if (filterResource.value && permission.resource !== filterResource.value) {
      return false
    }
    if (filterAction.value && permission.action !== filterAction.value) {
      return false
    }
    return true
  })
})

const resourceRule = (v: string) =>
  /^[a-z][a-z0-9_]*$/.test(v) || 'Lowercase; start with a letter; only a-z, 0-9, _'

const actionRule = (v: string | null) =>
  Boolean(v && predefinedActions.includes(v as (typeof predefinedActions)[number])) ||
  'Select a standard action'

function openCreate() {
  createForm.resource = ''
  createForm.action = null
  createForm.name = ''
  createForm.description = ''
  createOpen.value = true
}

function openEdit(permission: PermissionResponse) {
  selected.value = permission
  editForm.name = permission.name
  editForm.description = permission.description
  editForm.is_active = permission.is_active
  editOpen.value = true
}

async function load() {
  loading.value = true
  try {
    const { data } = await permissionsApi.list()
    permissions.value = data
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to load permissions'),
    })
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  if (!generatedCode.value) return
  saving.value = true
  try {
    await permissionsApi.create({
      code: generatedCode.value,
      name: createForm.name,
      description: createForm.description,
    })
    createOpen.value = false
    $q.notify({ type: 'positive', message: 'Permission created' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to create permission') })
  } finally {
    saving.value = false
  }
}

async function submitEdit() {
  if (!selected.value) return
  saving.value = true
  try {
    await permissionsApi.update(selected.value.id, {
      name: editForm.name,
      description: editForm.description,
      is_active: editForm.is_active,
    })
    editOpen.value = false
    $q.notify({ type: 'positive', message: 'Permission updated' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to update permission'),
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(permission: PermissionResponse) {
  $q.dialog({
    title: 'Delete permission',
    message: `Permanently remove ${permission.code}?`,
    cancel: { flat: true, label: 'Cancel', color: 'primary' },
    ok: { unelevated: true, label: 'Delete', color: 'negative' },
    persistent: true,
  }).onOk(() => {
    void deletePermission(permission)
  })
}

async function deletePermission(permission: PermissionResponse) {
  try {
    await permissionsApi.remove(permission.id)
    $q.notify({ type: 'positive', message: 'Permission deleted' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to delete permission'),
    })
  }
}

function clearFilters() {
  filterResource.value = null
  filterAction.value = null
}

onMounted(() => {
  void load()
})
</script>

<template>
  <q-page class="app-page">
    <q-card
      class="app-page__card"
      flat
    >
      <q-card-section class="app-page__section">
        <header class="app-page__header">
          <div>
            <h1 class="app-page__title">Permissions</h1>
            <p class="app-page__lead">
              Register canonical codes in resource.action format, with metadata for filtering and UI.
            </p>
          </div>
          <q-btn
            v-if="can(PermissionCode.PERMISSIONS_CREATE)"
            unelevated
            no-caps
            icon="add"
            label="New permission"
            class="app-page__btn-primary"
            @click="openCreate"
          />
        </header>

        <div class="app-page__filters">
          <q-select
            v-model="filterResource"
            :options="resourceOptions"
            label="Resource"
            outlined
            dense
            clearable
            class="app-page__filters-field"
          />
          <q-select
            v-model="filterAction"
            :options="filterActionOptions"
            label="Action"
            outlined
            dense
            clearable
            use-input
            fill-input
            hide-selected
            input-debounce="0"
            class="app-page__filters-field"
          />
          <q-btn
            flat
            no-caps
            color="primary"
            label="Clear"
            :disable="!filterResource && !filterAction"
            @click="clearFilters"
          />
        </div>

        <q-table
          class="app-page__table"
          flat
          bordered
          row-key="id"
          :rows="filteredPermissions"
          :columns="columns"
          :loading="loading"
          :rows-per-page-options="[10, 20, 50]"
        >
          <template #body-cell-code="props">
            <q-td :props="props">
              <code class="app-page__code">{{ props.row.code }}</code>
            </q-td>
          </template>

          <template #body-cell-resource="props">
            <q-td :props="props">
              <span class="app-page__chip">{{ props.row.resource }}</span>
            </q-td>
          </template>

          <template #body-cell-action="props">
            <q-td :props="props">
              <span class="app-page__chip app-page__chip--muted">{{ props.row.action }}</span>
            </q-td>
          </template>

          <template #body-cell-description="props">
            <q-td :props="props">
              <span class="app-page__muted">{{ props.row.description || '—' }}</span>
            </q-td>
          </template>

          <template #body-cell-is_active="props">
            <q-td :props="props">
              <q-badge
                :color="props.row.is_active ? 'primary' : 'grey'"
                :label="props.row.is_active ? 'Yes' : 'No'"
              />
            </q-td>
          </template>

          <template #body-cell-actions="props">
            <q-td :props="props">
              <div class="app-page__table-actions">
                <q-btn
                  v-if="can(PermissionCode.PERMISSIONS_UPDATE)"
                  flat
                  dense
                  round
                  icon="edit"
                  color="primary"
                  @click="openEdit(props.row)"
                >
                  <q-tooltip>Edit</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="can(PermissionCode.PERMISSIONS_DELETE)"
                  flat
                  dense
                  round
                  icon="delete"
                  color="negative"
                  @click="confirmDelete(props.row)"
                >
                  <q-tooltip>Delete</q-tooltip>
                </q-btn>
              </div>
            </q-td>
          </template>

          <template #no-data>
            <div class="app-page__empty">
              No permissions found.
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <q-dialog
      v-model="createOpen"
      persistent
    >
      <q-card class="app-page__dialog">
        <q-card-section>
          <div
            class="text-h6"
            style="color: #111827"
          >
            New permission
          </div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="createForm.resource"
              label="Resource"
              outlined
              dense
              required
              hint="e.g. users, reports"
              :rules="[resourceRule]"
              @update:model-value="(v) => { createForm.resource = String(v ?? '').toLowerCase() }"
            />
            <q-select
              v-model="createForm.action"
              :options="predefinedActions"
              label="Action"
              outlined
              dense
              required
              emit-value
              map-options
              :rules="[actionRule]"
            />
            <q-input
              :model-value="generatedCode"
              label="Code"
              outlined
              dense
              readonly
              hint="Generated as resource.action"
            />
            <q-input
              v-model="createForm.name"
              label="Name"
              outlined
              dense
              required
            />
            <q-input
              v-model="createForm.description"
              label="Description"
              outlined
              dense
              type="textarea"
              autogrow
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn
              flat
              no-caps
              label="Cancel"
              color="primary"
              @click="createOpen = false"
            />
            <q-btn
              type="submit"
              unelevated
              no-caps
              color="primary"
              label="Create"
              :loading="saving"
            />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog
      v-model="editOpen"
      persistent
    >
      <q-card class="app-page__dialog">
        <q-card-section>
          <div
            class="text-h6"
            style="color: #111827"
          >
            Edit permission
          </div>
          <div class="app-page__dialog-sub">
            <code>{{ selected?.code }}</code>
            <span v-if="selected"> · {{ selected.resource }} / {{ selected.action }}</span>
          </div>
        </q-card-section>
        <q-form @submit.prevent="submitEdit">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="editForm.name"
              label="Name"
              outlined
              dense
              required
            />
            <q-input
              v-model="editForm.description"
              label="Description"
              outlined
              dense
              type="textarea"
              autogrow
            />
            <q-toggle
              v-model="editForm.is_active"
              label="Permission active"
              color="primary"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn
              flat
              no-caps
              label="Cancel"
              color="primary"
              @click="editOpen = false"
            />
            <q-btn
              type="submit"
              unelevated
              no-caps
              color="primary"
              label="Save"
              :loading="saving"
            />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>
  </q-page>
</template>

