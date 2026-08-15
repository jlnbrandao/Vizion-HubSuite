<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import {
  apiErrorMessage,
  rolesApi,
  usersApi,
} from '@/services/api'
import type { RoleResponse, UserResponse } from '@/types/api'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const users = ref<UserResponse[]>([])
const roles = ref<RoleResponse[]>([])

const createOpen = ref(false)
const editOpen = ref(false)
const rolesOpen = ref(false)
const selected = ref<UserResponse | null>(null)

const createForm = reactive({
  email: '',
  username: '',
  full_name: '',
  password: '',
  role_ids: [] as string[],
})

const editForm = reactive({
  username: '',
  full_name: '',
  is_active: true,
  new_password: '',
})

const rolesForm = reactive({
  role_ids: [] as string[],
})

const roleOptions = computed(() =>
  roles.value.map((role) => ({
    label: role.name,
    value: role.id,
    description: role.description,
  })),
)

const roleNameById = computed(() => {
  const map = new Map<string, string>()
  for (const role of roles.value) {
    map.set(role.id, role.name)
  }
  return map
})

const columns: QTableColumn[] = [
  { name: 'username', label: 'Username', field: 'username', align: 'left', sortable: true },
  { name: 'full_name', label: 'Name', field: 'full_name', align: 'left', sortable: true },
  { name: 'email', label: 'Email', field: 'email', align: 'left', sortable: true },
  { name: 'roles', label: 'Roles', field: 'role_ids', align: 'left' },
  { name: 'is_active', label: 'Active', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
]

const usernameRule = (v: string) =>
  /^[a-z0-9][a-z0-9._-]{2,31}$/.test(v) ||
  '3–32 lowercase chars: letters, numbers, and only . - _'

function roleLabels(roleIds: string[]): string {
  if (!roleIds.length) return '—'
  return roleIds.map((id) => roleNameById.value.get(id) ?? id.slice(0, 8)).join(', ')
}

function resetCreateForm() {
  createForm.email = ''
  createForm.username = ''
  createForm.full_name = ''
  createForm.password = ''
  createForm.role_ids = []
}

function openCreate() {
  resetCreateForm()
  createOpen.value = true
}

function openEdit(user: UserResponse) {
  selected.value = user
  editForm.username = user.username
  editForm.full_name = user.full_name
  editForm.is_active = user.is_active
  editForm.new_password = ''
  editOpen.value = true
}

function openRoles(user: UserResponse) {
  selected.value = user
  rolesForm.role_ids = [...user.role_ids]
  rolesOpen.value = true
}

async function load() {
  loading.value = true
  try {
    const [usersRes, rolesRes] = await Promise.all([
      usersApi.list(),
      rolesApi.list(),
    ])
    users.value = usersRes.data
    roles.value = rolesRes.data
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load users') })
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  saving.value = true
  try {
    await usersApi.create({
      email: createForm.email,
      username: createForm.username.trim().toLowerCase(),
      full_name: createForm.full_name,
      password: createForm.password,
      role_ids: createForm.role_ids,
    })
    createOpen.value = false
    $q.notify({ type: 'positive', message: 'User created' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to create user') })
  } finally {
    saving.value = false
  }
}

async function submitEdit() {
  if (!selected.value) return
  saving.value = true
  try {
    await usersApi.update(selected.value.id, {
      username: editForm.username.trim().toLowerCase(),
      full_name: editForm.full_name,
      is_active: editForm.is_active,
    })
    if (editForm.new_password) {
      await usersApi.changePassword(selected.value.id, {
        new_password: editForm.new_password,
      })
    }
    editOpen.value = false
    $q.notify({ type: 'positive', message: 'User updated' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to update user') })
  } finally {
    saving.value = false
  }
}

async function submitRoles() {
  if (!selected.value) return
  saving.value = true
  try {
    await usersApi.replaceRoles(selected.value.id, rolesForm.role_ids)
    rolesOpen.value = false
    $q.notify({ type: 'positive', message: 'Roles updated' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to assign roles') })
  } finally {
    saving.value = false
  }
}

function confirmDelete(user: UserResponse) {
  $q.dialog({
    title: 'Delete user',
    message: `Permanently remove ${user.full_name}?`,
    cancel: { flat: true, label: 'Cancel', color: 'primary' },
    ok: { unelevated: true, label: 'Delete', color: 'negative' },
    persistent: true,
  }).onOk(() => {
    void deleteUser(user)
  })
}

async function deleteUser(user: UserResponse) {
  try {
    await usersApi.remove(user.id)
    $q.notify({ type: 'positive', message: 'User deleted' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to delete user') })
  }
}

async function consumeCreateQuery() {
  if (route.query.create !== '1') return
  if (!can(PermissionCode.USERS_CREATE)) {
    await router.replace({ path: '/users', query: {} })
    return
  }
  openCreate()
  await router.replace({ path: '/users', query: {} })
}

watch(
  () => route.query.create,
  () => {
    void consumeCreateQuery()
  },
)

onMounted(async () => {
  await load()
  await consumeCreateQuery()
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
            <h1 class="app-page__title">Users</h1>
            <p class="app-page__lead">
              Create accounts, change status, and assign RBAC roles.
            </p>
          </div>
          <q-btn
            v-if="can(PermissionCode.USERS_CREATE)"
            unelevated
            no-caps
            icon="person_add"
            label="New user"
            class="app-page__btn-primary"
            @click="openCreate"
          />
        </header>

        <q-table
          class="app-page__table"
          flat
          bordered
          row-key="id"
          :rows="users"
          :columns="columns"
          :loading="loading"
          :rows-per-page-options="[10, 20, 50]"
        >
          <template #body-cell-username="props">
            <q-td :props="props">
              <code class="app-page__code">{{ props.row.username }}</code>
            </q-td>
          </template>

          <template #body-cell-roles="props">
            <q-td :props="props">
              <span class="app-page__muted">{{ roleLabels(props.row.role_ids) }}</span>
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
                  v-if="can(PermissionCode.USERS_UPDATE)"
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
                  v-if="can(PermissionCode.USERS_ASSIGN)"
                  flat
                  dense
                  round
                  icon="shield"
                  color="primary"
                  @click="openRoles(props.row)"
                >
                  <q-tooltip>Roles</q-tooltip>
                </q-btn>
                <q-btn
                  v-if="can(PermissionCode.USERS_DELETE)"
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
              No users found.
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
            New user
          </div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="createForm.full_name"
              label="Full name"
              outlined
              dense
              required
              :rules="[(v) => (v && v.length >= 2) || 'Minimum 2 characters']"
            />
            <q-input
              v-model="createForm.username"
              label="Username"
              outlined
              dense
              required
              hint="Lowercase; numbers; special: . - _"
              :rules="[usernameRule]"
              @update:model-value="(v) => { createForm.username = String(v ?? '').toLowerCase() }"
            />
            <q-input
              v-model="createForm.email"
              type="email"
              label="Email"
              outlined
              dense
              required
            />
            <q-input
              v-model="createForm.password"
              type="password"
              label="Password"
              outlined
              dense
              required
              :rules="[(v) => (v && v.length >= 8) || 'Minimum 8 characters']"
            />
            <q-select
              v-model="createForm.role_ids"
              :options="roleOptions"
              label="Roles"
              outlined
              dense
              multiple
              emit-value
              map-options
              use-chips
              clearable
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
            Edit user
          </div>
          <div class="app-page__dialog-sub">
            <code>{{ selected?.username }}</code> · {{ selected?.email }}
          </div>
        </q-card-section>
        <q-form @submit.prevent="submitEdit">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="editForm.username"
              label="Username"
              outlined
              dense
              required
              :rules="[usernameRule]"
              @update:model-value="(v) => { editForm.username = String(v ?? '').toLowerCase() }"
            />
            <q-input
              v-model="editForm.full_name"
              label="Full name"
              outlined
              dense
              required
              :rules="[(v) => (v && v.length >= 2) || 'Minimum 2 characters']"
            />
            <q-toggle
              v-model="editForm.is_active"
              label="User active"
              color="primary"
            />
            <q-input
              v-model="editForm.new_password"
              type="password"
              label="New password (optional)"
              outlined
              dense
              hint="Leave blank to keep the current password"
              :rules="[
                (v) => !v || v.length >= 8 || 'Minimum 8 characters',
              ]"
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

    <q-dialog
      v-model="rolesOpen"
      persistent
    >
      <q-card class="app-page__dialog">
        <q-card-section>
          <div
            class="text-h6"
            style="color: #111827"
          >
            Assign roles
          </div>
          <div class="app-page__dialog-sub">{{ selected?.full_name }}</div>
        </q-card-section>
        <q-form @submit.prevent="submitRoles">
          <q-card-section>
            <q-select
              v-model="rolesForm.role_ids"
              :options="roleOptions"
              label="Roles"
              outlined
              dense
              multiple
              emit-value
              map-options
              use-chips
              clearable
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn
              flat
              no-caps
              label="Cancel"
              color="primary"
              @click="rolesOpen = false"
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

