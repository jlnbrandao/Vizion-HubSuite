<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { api, apiErrorMessage } from '@/services/api'

interface AuthPolicy {
  max_failed_attempts: number
  lockout_minutes: number
  password_min_age_hours: number
  password_max_age_days: number
  password_history_count: number
  session_idle_minutes: number
  mfa_required: string
  allowed_amr: string[]
  ip_allowlist: string[]
  password_login_enabled: boolean
  jit_provisioning_enabled: boolean
}

interface AccessPolicy {
  id: string
  name: string
  effect: 'allow' | 'deny'
  actions: string[]
  conditions: Record<string, unknown>
  priority: number
  is_active: boolean
}

const $q = useQuasar()
const { can } = usePermissions()

const loading = ref(false)
const savingAuth = ref(false)
const savingPolicy = ref(false)
const accessPolicies = ref<AccessPolicy[]>([])
const formOpen = ref(false)

const authPolicy = reactive<AuthPolicy>({
  max_failed_attempts: 5,
  lockout_minutes: 15,
  password_min_age_hours: 0,
  password_max_age_days: 0,
  password_history_count: 0,
  session_idle_minutes: 0,
  mfa_required: 'optional',
  allowed_amr: [],
  ip_allowlist: [],
  password_login_enabled: true,
  jit_provisioning_enabled: false,
})

const form = reactive({
  name: '',
  description: '',
  effect: 'deny' as 'allow' | 'deny',
  actions: [] as string[],
  resource_types: [] as string[],
  priority: 100,
  conditions: '{\n  "ip_allowlist": []\n}',
})

const mfaOptions = [
  { label: 'Optional — user decides', value: 'optional' },
  { label: 'Required for everyone', value: 'required' },
  { label: 'Disabled', value: 'disabled' },
]

const effectOptions = [
  { label: 'Deny (blocks what RBAC allowed)', value: 'deny' },
  { label: 'Allow (narrows an existing grant)', value: 'allow' },
]

const columns: QTableColumn[] = [
  { name: 'effect', label: 'Effect', field: 'effect', align: 'left', sortable: true },
  { name: 'name', label: 'Policy', field: 'name', align: 'left', sortable: true },
  { name: 'actions_list', label: 'Actions', field: 'actions', align: 'left' },
  { name: 'conditions', label: 'Conditions', field: 'conditions', align: 'left' },
  { name: 'priority', label: 'Priority', field: 'priority', align: 'right', sortable: true },
  { name: 'is_active', label: 'Active', field: 'is_active', align: 'center' },
]

async function loadAuthPolicy() {
  try {
    const { data } = await api.get<AuthPolicy>('/auth-policies')
    Object.assign(authPolicy, data)
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to load the authentication policy'),
    })
  }
}

async function loadAccessPolicies() {
  loading.value = true
  try {
    const { data } = await api.get<AccessPolicy[]>('/access-policies')
    accessPolicies.value = data
  } catch (error) {
    $q.notify({
      type: 'negative',
      message: apiErrorMessage(error, 'Failed to load access policies'),
    })
  } finally {
    loading.value = false
  }
}

async function saveAuthPolicy() {
  savingAuth.value = true
  try {
    await api.put('/auth-policies', authPolicy)
    $q.notify({ type: 'positive', message: 'Authentication policy saved' })
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to save the policy') })
  } finally {
    savingAuth.value = false
  }
}

function openCreate() {
  if (!can(PermissionCode.POLICIES_CREATE)) return
  form.name = ''
  form.description = ''
  form.effect = 'deny'
  form.actions = []
  form.resource_types = []
  form.priority = 100
  form.conditions = '{\n  "ip_allowlist": []\n}'
  formOpen.value = true
}

async function submitPolicy() {
  let conditions: Record<string, unknown>
  try {
    conditions = JSON.parse(form.conditions || '{}')
  } catch {
    $q.notify({ type: 'negative', message: 'Conditions must be valid JSON' })
    return
  }

  savingPolicy.value = true
  try {
    await api.post('/access-policies', {
      name: form.name.trim(),
      description: form.description.trim(),
      effect: form.effect,
      actions: form.actions,
      resource_types: form.resource_types,
      conditions,
      priority: form.priority,
    })
    $q.notify({ type: 'positive', message: 'Access policy created' })
    formOpen.value = false
    await loadAccessPolicies()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to create the policy') })
  } finally {
    savingPolicy.value = false
  }
}

onMounted(() => {
  void loadAuthPolicy()
  void loadAccessPolicies()
})
</script>

<template>
  <q-page class="app-page q-pa-md">
    <q-card flat bordered class="app-page__card q-mb-md">
      <q-card-section class="app-page__section">
        <div class="app-page__header">
          <div>
            <h1 class="app-page__title">Access policies</h1>
            <p class="app-page__lead">
              Authentication rules for the tenant plus the attribute-based (ABAC) policies
              evaluated after RBAC. ABAC can only narrow access: it never grants a permission the
              user's roles do not already have.
            </p>
          </div>
          <div class="app-page__actions">
            <q-btn
              v-if="can(PermissionCode.POLICIES_CREATE)"
              class="app-page__btn-primary"
              unelevated
              icon="add"
              label="New ABAC policy"
              @click="openCreate"
            />
          </div>
        </div>
      </q-card-section>
    </q-card>

    <q-card flat bordered class="app-page__card q-mb-md">
      <q-card-section>
        <div class="text-subtitle1">Authentication policy</div>
        <div class="text-caption text-grey-7">
          Applies to every sign-in of this tenant, including federated logins.
        </div>
      </q-card-section>
      <q-card-section class="row q-col-gutter-md">
        <q-input
          v-model.number="authPolicy.max_failed_attempts"
          class="col-12 col-sm-6 col-md-3"
          type="number"
          label="Max failed attempts"
          outlined
          dense
        />
        <q-input
          v-model.number="authPolicy.lockout_minutes"
          class="col-12 col-sm-6 col-md-3"
          type="number"
          label="Lockout (minutes)"
          outlined
          dense
        />
        <q-input
          v-model.number="authPolicy.password_max_age_days"
          class="col-12 col-sm-6 col-md-3"
          type="number"
          label="Password max age (days)"
          hint="0 disables expiry"
          outlined
          dense
        />
        <q-input
          v-model.number="authPolicy.password_history_count"
          class="col-12 col-sm-6 col-md-3"
          type="number"
          label="Password history"
          hint="Reuse blocked for N passwords"
          outlined
          dense
        />
        <q-input
          v-model.number="authPolicy.session_idle_minutes"
          class="col-12 col-sm-6 col-md-3"
          type="number"
          label="Session idle (minutes)"
          hint="0 keeps the default"
          outlined
          dense
        />
        <q-select
          v-model="authPolicy.mfa_required"
          class="col-12 col-sm-6 col-md-3"
          :options="mfaOptions"
          label="MFA"
          outlined
          dense
          emit-value
          map-options
        />
        <q-select
          v-model="authPolicy.ip_allowlist"
          class="col-12 col-md-6"
          label="IP allowlist"
          hint="Empty means any address; CIDR accepted"
          outlined
          dense
          use-input
          use-chips
          multiple
          hide-dropdown-icon
          new-value-mode="add-unique"
          :options="[]"
        />
        <div class="col-12 row q-col-gutter-md">
          <q-toggle
            v-model="authPolicy.password_login_enabled"
            class="col-12 col-sm-6"
            label="Allow password login"
          />
          <q-toggle
            v-model="authPolicy.jit_provisioning_enabled"
            class="col-12 col-sm-6"
            label="Just-in-time provisioning for federated users"
          />
        </div>
      </q-card-section>
      <q-card-actions align="right">
        <q-btn
          v-if="can(PermissionCode.POLICIES_UPDATE)"
          unelevated
          color="primary"
          label="Save policy"
          :loading="savingAuth"
          @click="saveAuthPolicy"
        />
      </q-card-actions>
    </q-card>

    <q-card flat bordered class="app-page__card">
      <q-card-section>
        <div class="text-subtitle1">ABAC policies</div>
        <div class="text-caption text-grey-7">
          Evaluated last, lowest priority number first. A matching deny stops the request.
        </div>
      </q-card-section>
      <q-card-section class="q-pt-none">
        <q-table
          flat
          bordered
          row-key="id"
          :rows="accessPolicies"
          :columns="columns"
          :loading="loading"
          :pagination="{ rowsPerPage: 10, sortBy: 'priority' }"
        >
          <template #body-cell-effect="props">
            <q-td :props="props">
              <q-badge :color="props.row.effect === 'deny' ? 'negative' : 'positive'">
                {{ String(props.row.effect).toUpperCase() }}
              </q-badge>
            </q-td>
          </template>
          <template #body-cell-actions_list="props">
            <q-td :props="props">
              <q-badge
                v-for="action in props.row.actions"
                :key="action"
                class="q-mr-xs"
                color="primary"
                outline
              >
                {{ action }}
              </q-badge>
              <span v-if="!props.row.actions.length">any action</span>
            </q-td>
          </template>
          <template #body-cell-conditions="props">
            <q-td :props="props">
              <code class="text-caption">{{ JSON.stringify(props.row.conditions) }}</code>
            </q-td>
          </template>
          <template #body-cell-is_active="props">
            <q-td :props="props">
              <q-icon
                :name="props.row.is_active ? 'check_circle' : 'cancel'"
                :color="props.row.is_active ? 'positive' : 'grey-6'"
                size="sm"
              />
            </q-td>
          </template>
          <template #no-data>
            <div class="full-width row flex-center text-grey-7 q-gutter-sm q-pa-md">
              <q-icon name="rule" size="md" />
              <span>No ABAC policies — RBAC decides alone.</span>
            </div>
          </template>
        </q-table>
      </q-card-section>
    </q-card>

    <q-dialog v-model="formOpen" persistent>
      <q-card class="app-page__dialog" style="min-width: min(560px, 96vw)">
        <q-card-section>
          <div class="text-h6">New ABAC policy</div>
          <div class="app-page__dialog-sub">
            Conditions are matched against the request context (subject, resource, environment).
          </div>
        </q-card-section>
        <q-card-section class="q-pt-none">
          <q-form class="q-gutter-md" @submit.prevent="submitPolicy">
            <q-input
              v-model="form.name"
              label="Name"
              outlined
              dense
              :rules="[(v) => !!String(v).trim() || 'Name is required']"
            />
            <q-input v-model="form.description" label="Description" outlined dense />
            <q-select
              v-model="form.effect"
              :options="effectOptions"
              label="Effect"
              outlined
              dense
              emit-value
              map-options
            />
            <q-select
              v-model="form.actions"
              label="Actions (permission codes)"
              hint="Empty applies to every action"
              outlined
              dense
              use-input
              use-chips
              multiple
              hide-dropdown-icon
              new-value-mode="add-unique"
              :options="[]"
            />
            <q-select
              v-model="form.resource_types"
              label="Resource types"
              hint="Empty applies to every resource"
              outlined
              dense
              use-input
              use-chips
              multiple
              hide-dropdown-icon
              new-value-mode="add-unique"
              :options="[]"
            />
            <q-input
              v-model.number="form.priority"
              type="number"
              label="Priority"
              hint="Lower runs first"
              outlined
              dense
            />
            <q-input
              v-model="form.conditions"
              type="textarea"
              label="Conditions (JSON)"
              autogrow
              outlined
              dense
            />
            <div class="row justify-end q-gutter-sm">
              <q-btn flat label="Cancel" color="grey-8" @click="formOpen = false" />
              <q-btn
                type="submit"
                unelevated
                color="primary"
                label="Create"
                :loading="savingPolicy"
              />
            </div>
          </q-form>
        </q-card-section>
      </q-card>
    </q-dialog>
  </q-page>
</template>
