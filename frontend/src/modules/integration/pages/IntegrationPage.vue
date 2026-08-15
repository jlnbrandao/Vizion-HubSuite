<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { apiErrorMessage } from '@/services/api'
import IntegrationForm from '@/modules/integration/components/IntegrationForm.vue'
import IntegrationLogs from '@/modules/integration/components/IntegrationLogs.vue'
import IntegrationMethodTable from '@/modules/integration/components/IntegrationMethodTable.vue'
import IntegrationStatus from '@/modules/integration/components/IntegrationStatus.vue'
import IntegrationSyncStatus from '@/modules/integration/components/IntegrationSyncStatus.vue'
import IntegrationTestResultPanel from '@/modules/integration/components/IntegrationTestResult.vue'
import {
  METHOD_COMPARISON,
  integrationService,
  methodLabel,
  type CreateIntegrationInput,
  type Integration,
  type IntegrationLogEntry,
  type IntegrationMethodType,
  type IntegrationSyncResult,
  type IntegrationTestResult,
  type UpdateIntegrationInput,
} from '@/modules/integration/data'

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const testing = ref(false)
const syncing = ref(false)
const logsLoading = ref(false)

const integrations = ref<Integration[]>([])
const selected = ref<Integration | null>(null)
const selectedMethod = ref<IntegrationMethodType | null>(null)
const formOpen = ref(false)
const editing = ref<Integration | null>(null)
/** Comparative method table modal — opened by "Nova integração". */
const methodPickerOpen = ref(false)

const testResult = ref<IntegrationTestResult | null>(null)
const lastSync = ref<IntegrationSyncResult | null>(null)
const logs = ref<IntegrationLogEntry[]>([])

const columns: QTableColumn[] = [
  { name: 'name', label: 'Nome', field: 'name', align: 'left', sortable: true },
  {
    name: 'type',
    label: 'Método',
    field: (row: Integration) => methodLabel(row.type),
    align: 'left',
    sortable: true,
  },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  {
    name: 'lastSyncAt',
    label: 'Última sync',
    field: 'lastSyncAt',
    align: 'left',
    sortable: true,
  },
  { name: 'actions', label: 'Ações', field: 'id', align: 'right' },
]

async function load() {
  loading.value = true
  try {
    integrations.value = await integrationService.list()
    if (selected.value) {
      selected.value =
        integrations.value.find((item) => item.id === selected.value?.id) ?? null
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Falha ao carregar integrações'),
    })
  } finally {
    loading.value = false
  }
}

async function loadLogs(id: string) {
  if (!can(PermissionCode.INTEGRATION_LOGS_READ)) {
    logs.value = []
    return
  }
  logsLoading.value = true
  try {
    logs.value = await integrationService.getLogs(id)
  } finally {
    logsLoading.value = false
  }
}

function selectRow(integration: Integration) {
  selected.value = integration
  testResult.value = null
  lastSync.value = null
  void loadLogs(integration.id)
}

function onTableSelected(rows: readonly Integration[]) {
  const row = rows[0]
  if (row) selectRow(row)
}

function openMethodPicker() {
  if (!can(PermissionCode.INTEGRATION_CREATE)) return
  methodPickerOpen.value = true
}

function closeMethodPicker() {
  methodPickerOpen.value = false
}

function openCreate(type: IntegrationMethodType) {
  if (!can(PermissionCode.INTEGRATION_CREATE)) return
  selectedMethod.value = type
  editing.value = null
  methodPickerOpen.value = false
  formOpen.value = true
}

function openEdit(integration: Integration) {
  if (!can(PermissionCode.INTEGRATION_UPDATE)) return
  editing.value = integration
  selectedMethod.value = integration.type
  formOpen.value = true
}

async function onFormSubmit(payload: CreateIntegrationInput) {
  saving.value = true
  try {
    if (editing.value) {
      const update: UpdateIntegrationInput = {
        name: payload.name,
        description: payload.description,
        status: payload.status,
        configuration: payload.configuration,
        secrets: payload.secrets,
      }
      const updated = await integrationService.update(editing.value.id, update)
      $q.notify({ type: 'positive', message: 'Integração atualizada' })
      formOpen.value = false
      await load()
      selectRow(updated)
    } else {
      const created = await integrationService.create(payload)
      $q.notify({ type: 'positive', message: 'Integração criada' })
      formOpen.value = false
      await load()
      selectRow(created)
    }
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Falha ao salvar integração'),
    })
  } finally {
    saving.value = false
  }
}

function confirmDelete(integration: Integration) {
  if (!can(PermissionCode.INTEGRATION_DELETE)) return
  $q.dialog({
    title: 'Excluir integração',
    message: `Remover "${integration.name}"?`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void removeIntegration(integration.id)
  })
}

async function removeIntegration(id: string) {
  try {
    await integrationService.remove(id)
    if (selected.value?.id === id) {
      selected.value = null
      logs.value = []
      testResult.value = null
      lastSync.value = null
    }
    $q.notify({ type: 'positive', message: 'Integração removida' })
    await load()
  } catch {
    $q.notify({ type: 'negative', message: 'Falha ao remover' })
  }
}

async function runTest(integration: Integration) {
  if (!can(PermissionCode.INTEGRATION_TEST)) return
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await integrationService.test(integration.id)
    await load()
    selectRow(
      integrations.value.find((item) => item.id === integration.id) ?? integration,
    )
  } finally {
    testing.value = false
  }
}

async function runSync(integration: Integration) {
  if (!can(PermissionCode.INTEGRATION_SYNC)) return
  syncing.value = true
  try {
    lastSync.value = await integrationService.sync(integration.id)
    $q.notify({
      type: lastSync.value.success ? 'positive' : 'negative',
      message: lastSync.value.message,
    })
    await load()
    const refreshed =
      integrations.value.find((item) => item.id === integration.id) ?? null
    if (refreshed) {
      selectRow(refreshed)
    }
  } finally {
    syncing.value = false
  }
}

function formatDate(value: string | null): string {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString()
  } catch {
    return value
  }
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
            <h1 class="app-page__title">Integrações</h1>
            <p class="app-page__lead">
              Hub de integração com sistemas terceiros. A UI fala só com o FastAPI; o
              RestProvider no backend executa as chamadas ao servidor terceiro.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn
              v-if="can(PermissionCode.INTEGRATION_CREATE)"
              class="app-page__btn-primary"
              unelevated
              icon="add"
              label="Nova integração"
              @click="openMethodPicker"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-lg-8">
        <q-card flat bordered class="app-page__card q-mb-md">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Integrações configuradas</div>
            <q-table
              flat
              bordered
              row-key="id"
              :rows="integrations"
              :columns="columns"
              :loading="loading"
              :pagination="{ rowsPerPage: 10 }"
              selection="single"
              :selected="selected ? [selected] : []"
              @update:selected="onTableSelected"
              @row-click="(_evt, row) => selectRow(row as Integration)"
            >
              <template #body-cell-status="props">
                <q-td :props="props">
                  <IntegrationStatus :status="props.row.status" />
                </q-td>
              </template>
              <template #body-cell-lastSyncAt="props">
                <q-td :props="props">{{ formatDate(props.row.lastSyncAt) }}</q-td>
              </template>
              <template #body-cell-actions="props">
                <q-td :props="props" class="q-gutter-xs">
                  <q-btn
                    v-if="can(PermissionCode.INTEGRATION_TEST)"
                    flat
                    dense
                    round
                    icon="wifi_tethering"
                    color="primary"
                    @click.stop="runTest(props.row)"
                  >
                    <q-tooltip>Testar conexão</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="can(PermissionCode.INTEGRATION_SYNC)"
                    flat
                    dense
                    round
                    icon="sync"
                    color="primary"
                    @click.stop="runSync(props.row)"
                  >
                    <q-tooltip>Sincronizar agora</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="can(PermissionCode.INTEGRATION_UPDATE)"
                    flat
                    dense
                    round
                    icon="edit"
                    color="grey-8"
                    @click.stop="openEdit(props.row)"
                  >
                    <q-tooltip>Editar</q-tooltip>
                  </q-btn>
                  <q-btn
                    v-if="can(PermissionCode.INTEGRATION_DELETE)"
                    flat
                    dense
                    round
                    icon="delete"
                    color="negative"
                    @click.stop="confirmDelete(props.row)"
                  >
                    <q-tooltip>Excluir</q-tooltip>
                  </q-btn>
                </q-td>
              </template>
            </q-table>
          </q-card-section>
        </q-card>

      </div>

      <div class="col-12 col-lg-4">
        <q-card flat bordered class="app-page__card q-mb-md">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Status / sync</div>
            <IntegrationSyncStatus
              :integration="selected"
              :last-sync="lastSync"
              :loading="syncing"
            />
            <div v-if="selected" class="q-mt-md q-gutter-sm">
              <q-btn
                v-if="can(PermissionCode.INTEGRATION_TEST)"
                unelevated
                color="primary"
                icon="wifi_tethering"
                label="Testar conexão"
                :loading="testing"
                @click="runTest(selected)"
              />
              <q-btn
                v-if="can(PermissionCode.INTEGRATION_SYNC)"
                outline
                color="primary"
                icon="sync"
                label="Sincronizar agora"
                :loading="syncing"
                @click="runSync(selected)"
              />
            </div>
          </q-card-section>
        </q-card>

        <q-card flat bordered class="app-page__card q-mb-md">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Resultado do teste</div>
            <IntegrationTestResultPanel :result="testResult" :loading="testing" />
          </q-card-section>
        </q-card>

        <q-card v-if="can(PermissionCode.INTEGRATION_LOGS_READ)" flat bordered class="app-page__card">
          <q-card-section>
            <div class="text-h6 q-mb-sm">Histórico / logs</div>
            <IntegrationLogs
              v-if="selected"
              :logs="logs"
              :loading="logsLoading"
            />
            <div v-else class="text-caption text-grey-6">
              Selecione uma integração para ver os logs.
            </div>
          </q-card-section>
        </q-card>
      </div>
    </div>

    <q-dialog
      v-model="methodPickerOpen"
      persistent
      transition-show="fade"
      transition-hide="fade"
      class="integration-hub-dialog"
    >
      <q-card flat class="integration-hub-modal">
        <header class="integration-hub-modal__titlebar">
          <div>
            <h2 class="integration-hub-modal__title">Tabela comparativa</h2>
            <p class="integration-hub-modal__lead">
              Escolha um método e clique em Usar para configurar a nova integração.
            </p>
          </div>
          <button
            type="button"
            class="integration-hub-modal__close-x"
            aria-label="Fechar"
            @click="closeMethodPicker"
          >
            <q-icon name="close" size="18px" />
          </button>
        </header>

        <div class="integration-hub-modal__body">
          <IntegrationMethodTable
            :rows="METHOD_COMPARISON"
            @select="openCreate"
          />
        </div>

        <footer class="integration-hub-modal__footer">
          <span class="integration-hub-modal__footer-hint">
            Classificações indicativas para orientação arquitetural.
          </span>
          <q-btn outline color="grey-8" label="Fechar" @click="closeMethodPicker" />
        </footer>
      </q-card>
    </q-dialog>

    <IntegrationForm
      v-model="formOpen"
      :method-type="selectedMethod"
      :integration="editing"
      :saving="saving"
      @submit="onFormSubmit"
    />
  </q-page>
</template>

