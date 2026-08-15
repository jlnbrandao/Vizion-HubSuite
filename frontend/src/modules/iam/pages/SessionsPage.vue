<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { api, apiErrorMessage } from '@/services/api'

interface SessionEntry {
  id: string
  amr: string[] | null
  ip_address: string | null
  user_agent: string | null
  created_at: string | null
  expires_at: string | null
  revoked_at: string | null
}

const $q = useQuasar()

const loading = ref(false)
const sessions = ref<SessionEntry[]>([])

const columns: QTableColumn[] = [
  { name: 'status', label: 'Status', field: 'revoked_at', align: 'left' },
  { name: 'device', label: 'Device', field: 'user_agent', align: 'left' },
  { name: 'ip_address', label: 'IP', field: 'ip_address', align: 'left' },
  { name: 'amr', label: 'Sign-in', field: 'amr', align: 'left' },
  { name: 'created_at', label: 'Started', field: 'created_at', align: 'left', sortable: true },
  { name: 'expires_at', label: 'Expires', field: 'expires_at', align: 'left' },
  { name: 'actions', label: '', field: 'id', align: 'right' },
]

const activeCount = computed(() => sessions.value.filter((row) => !row.revoked_at).length)

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : '—'
}

/** Keeps the table readable without pretending to be full UA parsing. */
function deviceLabel(userAgent: string | null): string {
  if (!userAgent) return 'Unknown device'
  const match = /(Firefox|Edg|Chrome|Safari)\/[\d.]+/.exec(userAgent)
  const browser = match ? match[1].replace('Edg', 'Edge') : 'Browser'
  const platform = /Windows/.test(userAgent)
    ? 'Windows'
    : /Android/.test(userAgent)
      ? 'Android'
      : /(iPhone|iPad)/.test(userAgent)
        ? 'iOS'
        : /Mac OS/.test(userAgent)
          ? 'macOS'
          : /Linux/.test(userAgent)
            ? 'Linux'
            : 'Unknown OS'
  return `${browser} · ${platform}`
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get<SessionEntry[]>('/sessions')
    sessions.value = data
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load sessions') })
  } finally {
    loading.value = false
  }
}

function confirmRevoke(row: SessionEntry) {
  $q.dialog({
    title: 'Revoke session',
    message: `Sign out ${deviceLabel(row.user_agent)}? Its access token stops working immediately.`,
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void revoke(row.id)
  })
}

async function revoke(id: string) {
  try {
    await api.post(`/sessions/${id}/revoke`)
    $q.notify({ type: 'positive', message: 'Session revoked' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to revoke session') })
  }
}

function confirmRevokeAll() {
  $q.dialog({
    title: 'Revoke every session',
    message: 'All devices are signed out, including this one. You will need to log in again.',
    cancel: true,
    persistent: true,
  }).onOk(() => {
    void revokeAll()
  })
}

async function revokeAll() {
  try {
    await api.post('/sessions/revoke-all')
    $q.notify({ type: 'positive', message: 'All sessions revoked' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to revoke sessions') })
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
            <h1 class="app-page__title">My sessions</h1>
            <p class="app-page__lead">
              Every device signed in with your account. Revoking a session invalidates its refresh
              token and denylists its access token, so it loses access immediately.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn outline color="primary" icon="refresh" label="Reload" @click="load" />
            <q-btn
              :disable="activeCount === 0"
              color="negative"
              unelevated
              icon="logout"
              label="Revoke all"
              @click="confirmRevokeAll"
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
          :rows="sessions"
          :columns="columns"
          :loading="loading"
          :pagination="{ rowsPerPage: 10, sortBy: 'created_at', descending: true }"
        >
          <template #body-cell-status="props">
            <q-td :props="props">
              <q-badge :color="props.row.revoked_at ? 'grey-6' : 'positive'">
                {{ props.row.revoked_at ? 'REVOKED' : 'ACTIVE' }}
              </q-badge>
            </q-td>
          </template>
          <template #body-cell-device="props">
            <q-td :props="props">
              <div>{{ deviceLabel(props.row.user_agent) }}</div>
              <div class="text-caption text-grey-7 ellipsis" style="max-width: 320px">
                {{ props.row.user_agent || '—' }}
              </div>
            </q-td>
          </template>
          <template #body-cell-ip_address="props">
            <q-td :props="props">{{ props.row.ip_address || '—' }}</q-td>
          </template>
          <template #body-cell-amr="props">
            <q-td :props="props">
              <q-badge
                v-for="method in props.row.amr || []"
                :key="method"
                class="q-mr-xs"
                color="primary"
                outline
              >
                {{ method }}
              </q-badge>
              <span v-if="!(props.row.amr || []).length">—</span>
            </q-td>
          </template>
          <template #body-cell-created_at="props">
            <q-td :props="props">{{ formatDate(props.row.created_at) }}</q-td>
          </template>
          <template #body-cell-expires_at="props">
            <q-td :props="props">{{ formatDate(props.row.expires_at) }}</q-td>
          </template>
          <template #body-cell-actions="props">
            <q-td :props="props">
              <q-btn
                v-if="!props.row.revoked_at"
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
            <div class="full-width row flex-center text-grey-7 q-gutter-sm q-pa-md">
              <q-icon name="devices" size="md" />
              <span>No sessions recorded.</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>
  </q-page>
</template>
