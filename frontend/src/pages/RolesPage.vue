<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
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

const permsForm = reactive({
  permission_ids: [] as string[],
})

const permissionOptions = computed(() =>
  permissions.value.map((permission) => ({
    label: `${permission.code} — ${permission.name}`,
    value: permission.id,
  })),
)

const filteredPermissionOptions = ref<Array<{ label: string; value: string }>>([])

watch(
  permissionOptions,
  (opts) => {
    filteredPermissionOptions.value = opts
  },
  { immediate: true },
)

function filterPermissions(val: string, update: (fn: () => void) => void) {
  update(() => {
    const needle = val.toLowerCase()
    filteredPermissionOptions.value = needle
      ? permissionOptions.value.filter((opt) =>
          opt.label.toLowerCase().includes(needle),
        )
      : permissionOptions.value
  })
}

const columns: QTableColumn[] = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left', sortable: true },
  { name: 'description', label: 'Descrição', field: 'description', align: 'left' },
  { name: 'permissions', label: 'Permissões', field: 'permission_ids', align: 'center' },
  { name: 'is_active', label: 'Ativo', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Ações', field: 'id', align: 'right' },
]

const roleNameRule = (v: string) =>
  /^[A-Z][A-Z0-9_]{1,63}$/.test(v) || 'Use A-Z, números e _; comece com letra'

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
  permsForm.permission_ids = [...role.permission_ids]
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
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Falha ao carregar roles') })
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
    $q.notify({ type: 'positive', message: 'Role criada' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Falha ao criar role') })
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
    $q.notify({ type: 'positive', message: 'Role atualizada' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Falha ao atualizar role') })
  } finally {
    saving.value = false
  }
}

async function submitPermissions() {
  if (!selected.value) return
  saving.value = true
  try {
    await rolesApi.replacePermissions(selected.value.id, permsForm.permission_ids)
    permsOpen.value = false
    $q.notify({ type: 'positive', message: 'Permissões atualizadas' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Falha ao atribuir permissões'),
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(role: RoleResponse) {
  $q.dialog({
    title: 'Excluir role',
    message: `Remover permanentemente a role ${role.name}?`,
    cancel: { flat: true, label: 'Cancelar', color: 'primary' },
    ok: { unelevated: true, label: 'Excluir', color: 'negative' },
    persistent: true,
  }).onOk(() => {
    void deleteRole(role)
  })
}

async function deleteRole(role: RoleResponse) {
  try {
    await rolesApi.remove(role.id)
    $q.notify({ type: 'positive', message: 'Role excluída' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Falha ao excluir role') })
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <q-page class="admin-page">
    <header class="admin-page__header">
      <div>
        <p class="admin-page__eyebrow">Administração</p>
        <h1>Roles</h1>
        <p class="admin-page__lead">
          Defina papéis e associe o conjunto de permissões de cada um.
        </p>
      </div>
      <q-btn
        v-if="can(PermissionCode.ROLES_CREATE)"
        color="primary"
        unelevated
        no-caps
        icon="add"
        label="Nova role"
        @click="openCreate"
      />
    </header>

    <q-table
      class="admin-table"
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
          <span class="admin-table__muted">{{ props.row.description || '—' }}</span>
        </q-td>
      </template>

      <template #body-cell-permissions="props">
        <q-td :props="props">
          <q-badge
            color="teal"
            :label="String(props.row.permission_ids.length)"
          />
        </q-td>
      </template>

      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-badge
            :color="props.row.is_active ? 'teal' : 'grey'"
            :label="props.row.is_active ? 'Sim' : 'Não'"
          />
        </q-td>
      </template>

      <template #body-cell-actions="props">
        <q-td :props="props">
          <div class="admin-table__actions">
            <q-btn
              v-if="can(PermissionCode.ROLES_UPDATE)"
              flat
              dense
              round
              icon="edit"
              color="primary"
              @click="openEdit(props.row)"
            >
              <q-tooltip>Editar</q-tooltip>
            </q-btn>
            <q-btn
              v-if="can(PermissionCode.ROLES_ASSIGN_PERMISSIONS)"
              flat
              dense
              round
              icon="key"
              color="primary"
              @click="openPermissions(props.row)"
            >
              <q-tooltip>Permissões</q-tooltip>
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
              <q-tooltip>Excluir</q-tooltip>
            </q-btn>
          </div>
        </q-td>
      </template>

      <template #no-data>
        <div class="admin-table__empty">
          Nenhuma role encontrada.
        </div>
      </template>
    </q-table>

    <q-dialog
      v-model="createOpen"
      persistent
    >
      <q-card class="admin-dialog">
        <q-card-section>
          <div class="text-h6">Nova role</div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="createForm.name"
              label="Nome"
              outlined
              dense
              required
              hint="Ex.: ADMIN, MANAGER"
              :rules="[roleNameRule]"
              @update:model-value="(v) => { createForm.name = String(v ?? '').toUpperCase() }"
            />
            <q-input
              v-model="createForm.description"
              label="Descrição"
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
              label="Cancelar"
              color="primary"
              @click="createOpen = false"
            />
            <q-btn
              type="submit"
              unelevated
              no-caps
              color="primary"
              label="Criar"
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
      <q-card class="admin-dialog">
        <q-card-section>
          <div class="text-h6">Editar role</div>
          <div class="admin-dialog__sub">{{ selected?.name }}</div>
        </q-card-section>
        <q-form @submit.prevent="submitEdit">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="editForm.description"
              label="Descrição"
              outlined
              dense
              type="textarea"
              autogrow
            />
            <q-toggle
              v-model="editForm.is_active"
              label="Role ativa"
              color="primary"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn
              flat
              no-caps
              label="Cancelar"
              color="primary"
              @click="editOpen = false"
            />
            <q-btn
              type="submit"
              unelevated
              no-caps
              color="primary"
              label="Salvar"
              :loading="saving"
            />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>

    <q-dialog
      v-model="permsOpen"
      persistent
    >
      <q-card class="admin-dialog admin-dialog--wide">
        <q-card-section>
          <div class="text-h6">Atribuir permissões</div>
          <div class="admin-dialog__sub">{{ selected?.name }}</div>
        </q-card-section>
        <q-form @submit.prevent="submitPermissions">
          <q-card-section>
            <q-select
              v-model="permsForm.permission_ids"
              :options="filteredPermissionOptions"
              label="Permissões"
              outlined
              dense
              multiple
              emit-value
              map-options
              use-chips
              clearable
              use-input
              input-debounce="0"
              @filter="filterPermissions"
            />
          </q-card-section>
          <q-card-actions align="right">
            <q-btn
              flat
              no-caps
              label="Cancelar"
              color="primary"
              @click="permsOpen = false"
            />
            <q-btn
              type="submit"
              unelevated
              no-caps
              color="primary"
              label="Salvar"
              :loading="saving"
            />
          </q-card-actions>
        </q-form>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped lang="scss">
.admin-page {
  padding: 1.5rem 1.5rem 2.5rem;
  max-width: 1200px;
  margin: 0 auto;
}

.admin-page__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.admin-page__eyebrow {
  margin: 0 0 0.25rem;
  color: var(--ls-accent);
  font-size: 0.8rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.admin-page__header h1 {
  margin: 0 0 0.35rem;
  font-family: var(--ls-font-display);
  font-size: 1.85rem;
  font-weight: 600;
}

.admin-page__lead {
  margin: 0;
  color: var(--ls-muted);
  max-width: 36rem;
}

.admin-table {
  background: var(--ls-panel);
  border-radius: 12px;
  overflow: hidden;
}

.admin-table__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.15rem;
}

.admin-table__muted {
  color: var(--ls-muted);
  font-size: 0.9rem;
}

.admin-table__empty {
  padding: 2rem;
  text-align: center;
  color: var(--ls-muted);
}

.admin-dialog {
  min-width: min(440px, 92vw);
}

.admin-dialog--wide {
  min-width: min(560px, 94vw);
}

.admin-dialog__sub {
  margin-top: 0.2rem;
  color: var(--ls-muted);
  font-size: 0.9rem;
}
</style>
