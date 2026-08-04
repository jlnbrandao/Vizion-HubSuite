<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { apiErrorMessage, permissionsApi } from '@/services/api'
import type { PermissionResponse } from '@/types/api'

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const permissions = ref<PermissionResponse[]>([])

const createOpen = ref(false)
const editOpen = ref(false)
const selected = ref<PermissionResponse | null>(null)

const createForm = reactive({
  code: '',
  name: '',
  description: '',
})

const editForm = reactive({
  name: '',
  description: '',
  is_active: true,
})

const columns: QTableColumn[] = [
  { name: 'code', label: 'Código', field: 'code', align: 'left', sortable: true },
  { name: 'name', label: 'Nome', field: 'name', align: 'left', sortable: true },
  { name: 'description', label: 'Descrição', field: 'description', align: 'left' },
  { name: 'is_active', label: 'Ativo', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Ações', field: 'id', align: 'right' },
]

const codeRule = (v: string) =>
  /^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$/.test(v) || 'Formato: resource.action (minúsculas)'

function openCreate() {
  createForm.code = ''
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
      message: apiErrorMessage(error, 'Falha ao carregar permissões'),
    })
  } finally {
    loading.value = false
  }
}

async function submitCreate() {
  saving.value = true
  try {
    await permissionsApi.create({
      code: createForm.code.trim().toLowerCase(),
      name: createForm.name,
      description: createForm.description,
    })
    createOpen.value = false
    $q.notify({ type: 'positive', message: 'Permissão criada' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Falha ao criar permissão') })
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
    $q.notify({ type: 'positive', message: 'Permissão atualizada' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Falha ao atualizar permissão'),
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(permission: PermissionResponse) {
  $q.dialog({
    title: 'Excluir permissão',
    message: `Remover permanentemente ${permission.code}?`,
    cancel: { flat: true, label: 'Cancelar', color: 'primary' },
    ok: { unelevated: true, label: 'Excluir', color: 'negative' },
    persistent: true,
  }).onOk(() => {
    void deletePermission(permission)
  })
}

async function deletePermission(permission: PermissionResponse) {
  try {
    await permissionsApi.remove(permission.id)
    $q.notify({ type: 'positive', message: 'Permissão excluída' })
    await load()
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Falha ao excluir permissão'),
    })
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
        <h1>Permissões</h1>
        <p class="admin-page__lead">
          Cadastre códigos canônicos no formato resource.action.
        </p>
      </div>
      <q-btn
        v-if="can(PermissionCode.PERMISSIONS_CREATE)"
        color="primary"
        unelevated
        no-caps
        icon="add"
        label="Nova permissão"
        @click="openCreate"
      />
    </header>

    <q-table
      class="admin-table"
      flat
      bordered
      row-key="id"
      :rows="permissions"
      :columns="columns"
      :loading="loading"
      :rows-per-page-options="[10, 20, 50]"
    >
      <template #body-cell-code="props">
        <q-td :props="props">
          <code class="admin-table__code">{{ props.row.code }}</code>
        </q-td>
      </template>

      <template #body-cell-description="props">
        <q-td :props="props">
          <span class="admin-table__muted">{{ props.row.description || '—' }}</span>
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
              v-if="can(PermissionCode.PERMISSIONS_UPDATE)"
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
              v-if="can(PermissionCode.PERMISSIONS_DELETE)"
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
          Nenhuma permissão encontrada.
        </div>
      </template>
    </q-table>

    <q-dialog
      v-model="createOpen"
      persistent
    >
      <q-card class="admin-dialog">
        <q-card-section>
          <div class="text-h6">Nova permissão</div>
        </q-card-section>
        <q-form @submit.prevent="submitCreate">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="createForm.code"
              label="Código"
              outlined
              dense
              required
              hint="Ex.: users.export"
              :rules="[codeRule]"
              @update:model-value="(v) => { createForm.code = String(v ?? '').toLowerCase() }"
            />
            <q-input
              v-model="createForm.name"
              label="Nome"
              outlined
              dense
              required
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
          <div class="text-h6">Editar permissão</div>
          <div class="admin-dialog__sub">
            <code>{{ selected?.code }}</code>
          </div>
        </q-card-section>
        <q-form @submit.prevent="submitEdit">
          <q-card-section class="q-gutter-md">
            <q-input
              v-model="editForm.name"
              label="Nome"
              outlined
              dense
              required
            />
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
              label="Permissão ativa"
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

.admin-table__code {
  background: rgba(15, 118, 110, 0.1);
  padding: 0.15rem 0.4rem;
  border-radius: 6px;
  font-size: 0.85rem;
}

.admin-table__empty {
  padding: 2rem;
  text-align: center;
  color: var(--ls-muted);
}

.admin-dialog {
  min-width: min(440px, 92vw);
}

.admin-dialog__sub {
  margin-top: 0.2rem;
  color: var(--ls-muted);
  font-size: 0.9rem;
}

.admin-dialog__sub code {
  background: rgba(15, 118, 110, 0.1);
  padding: 0.1rem 0.35rem;
  border-radius: 6px;
}
</style>
