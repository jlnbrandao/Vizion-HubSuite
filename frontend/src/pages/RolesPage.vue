<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import AssignPermissionsDialog from '@/components/roles/AssignPermissionsDialog.vue'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import {
  apiErrorMessage,
  permissionsApi,
  rolesApi,
} from '@/services/api'
import type { PermissionResponse, RoleResponse } from '@/types/api'

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const roles = ref<RoleResponse[]>([])
const permissions = ref<PermissionResponse[]>([])

const createOpen = ref(false)
const editOpen = ref(false)
const permsOpen = ref(false)
const selected = ref<RoleResponse | null>(null)

const createForm = reactive({
  name: '',
  description: '',
})

const editForm = reactive({
  description: '',
  is_active: true,
})

const columns: QTableColumn[] = [
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'description', label: 'Description', field: 'description', align: 'left' },
  { name: 'permissions', label: 'Permissions', field: 'permission_ids', align: 'center' },
  { name: 'is_active', label: 'Active', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
]

const roleNameRule = (v: string) =>
  /^[A-Z][A-Z0-9_]{1,63}$/.test(v) || 'Use A–Z, numbers, and _; start with a letter'

function openCreate() {
  createForm.name = ''
  createForm.description = ''
  createOpen.value = true
}

function openEdit(role: RoleResponse) {
  selected.value = role
  editForm.description = role.description
  editForm.is_active = role.is_active
  editOpen.value = true
}

function openPermissions(role: RoleResponse) {
  selected.value = role
  permsOpen.value = true
}

async function load() {
  loading.value = true
  try {
    const [rolesRes, permsRes] = await Promise.all([
      rolesApi.list(),
      permissionsApi.list(),
    ])
    roles.value = rolesRes.data
    permissions.value = permsRes.data
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load roles') })
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  saving.value = true
  try {
    await rolesApi.create({
      name: createForm.name.trim().toUpperCase(),
      description: createForm.description,
    })
    createOpen.value = false
    $q.notify({ type: 'positive', message: 'Role created' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to create role') })
  } finally {
    saving.value = false
  }
}

async function submitEdit() {
  if (!selected.value) return
  saving.value = true
  try {
    await rolesApi.update(selected.value.id, {
      description: editForm.description,
      is_active: editForm.is_active,
    })
    editOpen.value = false
    $q.notify({ type: 'positive', message: 'Role updated' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to update role') })
  } finally {
    saving.value = false
  }
}

async function submitPermissions(permissionIds: string[]) {
  if (!selected.value) return
  saving.value = true
  try {
    await rolesApi.replacePermissions(selected.value.id, permissionIds)
    permsOpen.value = false
    $q.notify({ type: 'positive', message: 'Permissions updated' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to assign permissions'),
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(role: RoleResponse) {
  $q.dialog({
    title: 'Delete role',
    message: `Permanently remove role ${role.name}?`,
    cancel: { flat: true, label: 'Cancel', color: 'primary' },
    ok: { unelevated: true, label: 'Delete', color: 'negative' },
    persistent: true,
  }).onOk(() => {
    void deleteRole(role)
  })
}

async function deleteRole(role: RoleResponse) {
  try {
    await rolesApi.remove(role.id)
    $q.notify({ type: 'positive', message: 'Role deleted' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to delete role') })
  }
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
            <h1 class="app-page__title">Roles</h1>
            <p class="app-page__lead">
              Define roles and associate each one's permission set.
            </p>
          </div>
          <q-btn
            v-if="can(PermissionCode.ROLES_CREATE)"
            unelevated
            no-caps
            icon="add"
            label="New role"
            class="app-page__btn-primary"
            @click="openCreate"
          />
        </header>

        <q-table
          class="app-page__table"
          flat
          bordered
          row-key="id"
          :rows="roles"
          :columns="columns"
          :loading="loading"
          :rows-per-page-options="[10, 20, 50]"
        >
          <template #body-cell-description="props">
            <q-td :props="props">
              <span class="app-page__muted">{{ props.row.description || '—' }}</span>
            </q-td>
          </template>

          <template #body-cell-permissions="props">
            <q-td :props="props">
              <q-badge
                color="primary"
                :label="String(props.row.permission_ids.length)"
              />
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
                  v-if="can(PermissionCode.ROLES_UPDATE)"
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
                  v-if="can(PermissionCode.ROLES_ASSIGN)"
                  flat
                  dense
                  round
                  icon="key"
                  color="primary"
                  @click="openPermissions(props.row)"
                >
                  <q-tooltip>Permissions</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="can(PermissionCode.ROLES_DELETE)"
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
              No roles found.
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
            New role
          </div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="createForm.name"
              label="Name"
              outlined
              dense
              required
              hint="e.g. ADMIN, MANAGER"
              :rules="[roleNameRule]"
              @update:model-value="(v) => { createForm.name = String(v ?? '').toUpperCase() }"
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
            Edit role
          </div>
          <div class="app-page__dialog-sub">{{ selected?.name }}</div>
        </q-card-section>
        <q-form @submit.prevent="submitEdit">
          <q-card-section class="q-gutter-md">
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
              label="Role active"
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

    <AssignPermissionsDialog
      v-model="permsOpen"
      :role="selected"
      :roles="roles"
      :permissions="permissions"
      :saving="saving"
      @save="submitPermissions"
    />
  </q-page>
</template>

