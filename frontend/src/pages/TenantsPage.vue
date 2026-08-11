<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { apiErrorMessage, tenantsApi } from '@/services/api'
import type { TenantResponse } from '@/types/api'

const $q = useQuasar()
const route = useRoute()
const router = useRouter()
const { can } = usePermissions()

const loading = ref(false)
const saving = ref(false)
const tenants = ref<TenantResponse[]>([])
const createOpen = ref(false)
const renameOpen = ref(false)
const selected = ref<TenantResponse | null>(null)

const createForm = reactive({
  slug: '',
  name: '',
})

const renameForm = reactive({
  name: '',
})

const columns: QTableColumn[] = [
  { name: 'slug', label: 'Slug', field: 'slug', align: 'left', sortable: true },
  { name: 'name', label: 'Name', field: 'name', align: 'left', sortable: true },
  { name: 'is_active', label: 'Active', field: 'is_active', align: 'center' },
  { name: 'actions', label: 'Actions', field: 'id', align: 'right' },
]

const slugRule = (v: string) =>
  /^[a-z0-9]([a-z0-9-]{0,62}[a-z0-9])?$/.test(v) ||
  'Lowercase slug: letters, numbers, hyphens'

async function load() {
  loading.value = true
  try {
    const { data } = await tenantsApi.list()
    tenants.value = data
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Failed to load tenants') })
  } finally {
    loading.value = false
  }
}

function openCreate() {
  createForm.slug = ''
  createForm.name = ''
  createOpen.value = true
}

function openRename(tenant: TenantResponse) {
  selected.value = tenant
  renameForm.name = tenant.name
  renameOpen.value = true
}

async function submitCreate() {
  saving.value = true
  try {
    await tenantsApi.create({ slug: createForm.slug.trim(), name: createForm.name.trim() })
    createOpen.value = false
    $q.notify({ type: 'positive', message: 'Tenant created' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Create failed') })
  } finally {
    saving.value = false
  }
}

async function submitRename() {
  if (!selected.value) return
  saving.value = true
  try {
    await tenantsApi.rename(selected.value.id, { name: renameForm.name.trim() })
    renameOpen.value = false
    $q.notify({ type: 'positive', message: 'Tenant renamed' })
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Rename failed') })
  } finally {
    saving.value = false
  }
}

async function toggleActive(tenant: TenantResponse) {
  saving.value = true
  try {
    if (tenant.is_active) {
      await tenantsApi.deactivate(tenant.id)
      $q.notify({ type: 'positive', message: `Tenant ${tenant.slug} suspended` })
    } else {
      await tenantsApi.activate(tenant.id)
      $q.notify({ type: 'positive', message: `Tenant ${tenant.slug} activated` })
    }
    await load()
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Update failed') })
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  await load()
  if (route.query.create === '1' && can(PermissionCode.TENANTS_CREATE)) {
    openCreate()
    void router.replace({ path: '/tenants' })
  }
})

watch(
  () => route.query.create,
  (value) => {
    if (value === '1' && can(PermissionCode.TENANTS_CREATE)) {
      openCreate()
      void router.replace({ path: '/tenants' })
    }
  },
)
</script>

<template>
  <q-page class="app-page q-pa-md">
    <div class="row items-center q-mb-md">
      <div class="col">
        <div class="text-h5">Tenants</div>
        <div class="app-page__muted">Platform catalog of customer environments</div>
      </div>
      <div class="col-auto">
        <q-btn
          v-if="can(PermissionCode.TENANTS_CREATE)"
          color="primary"
          label="Create tenant"
          unelevated
          @click="openCreate"
        />
      </div>
    </div>

    <q-table
      flat
      bordered
      row-key="id"
      :rows="tenants"
      :columns="columns"
      :loading="loading"
      :pagination="{ rowsPerPage: 20 }"
    >
      <template #body-cell-is_active="props">
        <q-td :props="props">
          <q-badge :color="props.row.is_active ? 'positive' : 'grey'">
            {{ props.row.is_active ? 'Yes' : 'No' }}
          </q-badge>
        </q-td>
      </template>
      <template #body-cell-actions="props">
        <q-td :props="props" class="q-gutter-xs">
          <q-btn
            v-if="can(PermissionCode.TENANTS_UPDATE)"
            flat
            dense
            color="primary"
            label="Rename"
            @click="openRename(props.row)"
          />
          <q-btn
            v-if="props.row.is_active && can(PermissionCode.TENANTS_DEACTIVATE)"
            flat
            dense
            color="warning"
            label="Suspend"
            :disable="saving"
            @click="toggleActive(props.row)"
          />
          <q-btn
            v-if="!props.row.is_active && can(PermissionCode.TENANTS_ACTIVATE)"
            flat
            dense
            color="positive"
            label="Activate"
            :disable="saving"
            @click="toggleActive(props.row)"
          />
        </q-td>
      </template>
    </q-table>

    <q-dialog v-model="createOpen" persistent>
      <q-card style="min-width: 360px">
        <q-card-section class="text-h6">Create tenant</q-card-section>
        <q-card-section class="q-gutter-md">
          <q-input v-model="createForm.slug" label="Slug" :rules="[slugRule]" outlined dense />
          <q-input v-model="createForm.name" label="Name" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn
            color="primary"
            label="Create"
            unelevated
            :loading="saving"
            :disable="!createForm.slug.trim() || !createForm.name.trim()"
            @click="submitCreate"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <q-dialog v-model="renameOpen" persistent>
      <q-card style="min-width: 360px">
        <q-card-section class="text-h6">Rename tenant</q-card-section>
        <q-card-section>
          <q-input v-model="renameForm.name" label="Name" outlined dense />
        </q-card-section>
        <q-card-actions align="right">
          <q-btn flat label="Cancel" v-close-popup />
          <q-btn
            color="primary"
            label="Save"
            unelevated
            :loading="saving"
            :disable="!renameForm.name.trim()"
            @click="submitRename"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </q-page>
</template>
