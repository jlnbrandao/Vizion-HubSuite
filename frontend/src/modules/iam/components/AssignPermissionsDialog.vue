<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import { permissionService } from '@/constants/permissions'
import type { PermissionResponse, RoleResponse } from '@/types/api'

type ViewFilter = 'all' | 'assigned' | 'unassigned' | 'differences'

const props = defineProps<{
  modelValue: boolean
  role: RoleResponse | null
  roles: RoleResponse[]
  permissions: PermissionResponse[]
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [permissionIds: string[]]
}>()

const $q = useQuasar()

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const draftIds = ref<string[]>([])
const baselineIds = ref<string[]>([])
const search = ref('')
const appFilter = ref<string | null>(null)
const viewFilter = ref<ViewFilter>('all')
const compareRoleIds = ref<string[]>([])
const copyMenuOpen = ref(false)
const collapsedGroups = ref<Set<string>>(new Set())
const collapsedApps = ref<Set<string>>(new Set())

const MAX_COMPARE = 3

const CRITICAL_ACTIONS = new Set([
  'delete',
  'assign',
  'activate',
  'deactivate',
  'manage',
])

watch(
  () => [props.modelValue, props.role] as const,
  ([isOpen, role]) => {
    if (!isOpen || !role) return
    const ids = [...role.permission_ids]
    draftIds.value = ids
    baselineIds.value = [...ids]
    search.value = ''
    appFilter.value = null
    viewFilter.value = 'all'
    copyMenuOpen.value = false
    collapsedGroups.value = new Set()
    collapsedApps.value = new Set()
    compareRoleIds.value = []
  },
)

const draftSet = computed(() => new Set(draftIds.value))
const baselineSet = computed(() => new Set(baselineIds.value))

const assignedCount = computed(() => draftIds.value.length)

const isDirty = computed(() => {
  if (draftIds.value.length !== baselineIds.value.length) return true
  const base = baselineSet.value
  return draftIds.value.some((id) => !base.has(id))
})

const pendingCount = computed(() => {
  const base = baselineSet.value
  const draft = draftSet.value
  let added = 0
  let removed = 0
  for (const id of draft) if (!base.has(id)) added += 1
  for (const id of base) if (!draft.has(id)) removed += 1
  return added + removed
})

const roleDisplayName = computed(() =>
  props.role ? formatRoleLabel(props.role.name) : '',
)

const roleSlug = computed(() => (props.role ? props.role.name.toLowerCase() : ''))

const otherRoles = computed(() =>
  props.roles.filter((r) => r.id !== props.role?.id && r.is_active),
)

const compareRoles = computed(() =>
  compareRoleIds.value
    .map((id) => props.roles.find((r) => r.id === id))
    .filter((r): r is RoleResponse => Boolean(r)),
)

const availableCompareRoles = computed(() =>
  otherRoles.value.filter((r) => !compareRoleIds.value.includes(r.id)),
)

const appOptions = computed(() => {
  const apps = new Set(props.permissions.map((p) => permissionApp(p)))
  return [...apps].sort()
})

interface PermissionRow {
  permission: PermissionResponse
  app: string
  tela: string
  critical: boolean
  icon: string
  assigned: boolean
  compare: Array<{ roleId: string; assigned: boolean; differs: boolean }>
}

interface ResourceGroup {
  app: string
  tela: string
  key: string
  rows: PermissionRow[]
}

interface AppGroup {
  app: string
  resources: ResourceGroup[]
  rowCount: number
}

const enrichedRows = computed<PermissionRow[]>(() => {
  const compare = compareRoles.value
  const draft = draftSet.value
  return props.permissions
    .filter((p) => p.is_active)
    .map((permission) => {
      const assigned = draft.has(permission.id)
      return {
        permission,
        app: permissionApp(permission),
        tela: permission.resource.toUpperCase(),
        critical: CRITICAL_ACTIONS.has(permission.action),
        icon: actionIcon(permission.action),
        assigned,
        compare: compare.map((role) => {
          const roleAssigned = role.permission_ids.includes(permission.id)
          return {
            roleId: role.id,
            assigned: roleAssigned,
            differs: roleAssigned !== assigned,
          }
        }),
      }
    })
    .sort((a, b) => {
      const appCmp = a.app.localeCompare(b.app)
      if (appCmp !== 0) return appCmp
      const telaCmp = a.tela.localeCompare(b.tela)
      if (telaCmp !== 0) return telaCmp
      return a.permission.name.localeCompare(b.permission.name)
    })
})

const filteredRows = computed(() => {
  const needle = search.value.trim().toLowerCase()
  return enrichedRows.value.filter((row) => {
    if (appFilter.value && row.app !== appFilter.value) return false
    if (viewFilter.value === 'assigned' && !row.assigned) return false
    if (viewFilter.value === 'unassigned' && row.assigned) return false
    if (viewFilter.value === 'differences') {
      if (row.compare.length === 0 || !row.compare.some((c) => c.differs)) {
        return false
      }
    }
    if (!needle) return true
    return (
      row.permission.name.toLowerCase().includes(needle) ||
      row.permission.code.toLowerCase().includes(needle) ||
      row.tela.toLowerCase().includes(needle) ||
      row.app.toLowerCase().includes(needle)
    )
  })
})

const grouped = computed<AppGroup[]>(() => {
  const byApp = new Map<string, Map<string, PermissionRow[]>>()
  for (const row of filteredRows.value) {
    let byTela = byApp.get(row.app)
    if (!byTela) {
      byTela = new Map()
      byApp.set(row.app, byTela)
    }
    const list = byTela.get(row.tela) ?? []
    list.push(row)
    byTela.set(row.tela, list)
  }
  return [...byApp.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([app, byTela]) => {
      const resources = [...byTela.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([tela, rows]) => ({
          app,
          tela,
          key: `${app}::${tela}`,
          rows,
        }))
      return {
        app,
        resources,
        rowCount: resources.reduce((n, g) => n + g.rows.length, 0),
      }
    })
})

const footerStatus = computed(() => {
  if (!isDirty.value) return 'No pending changes'
  if (pendingCount.value === 1) return '1 pending change'
  return `${pendingCount.value} pending changes`
})

/** Permissions are grouped by the service that owns them (iam, platform, …). */
function permissionApp(permission: PermissionResponse): string {
  const service = permission.service || permissionService(permission.code)
  return (service || 'other').toUpperCase()
}

function formatRoleLabel(name: string): string {
  return name
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function actionIcon(action: string): string {
  const map: Record<string, string> = {
    create: 'add',
    read: 'search',
    update: 'edit',
    delete: 'delete',
    list: 'list',
    manage: 'settings',
    export: 'download',
    import: 'upload',
    approve: 'thumb_up',
    cancel: 'block',
    execute: 'play_arrow',
    assign: 'person_add',
    link: 'link',
    unlink: 'link_off',
    activate: 'toggle_on',
    deactivate: 'toggle_off',
  }
  return map[action] ?? 'vpn_key'
}

function setAssigned(permissionId: string, assigned: boolean) {
  const set = new Set(draftIds.value)
  if (assigned) set.add(permissionId)
  else set.delete(permissionId)
  draftIds.value = [...set]
}

function toggleAssigned(permissionId: string) {
  setAssigned(permissionId, !draftSet.value.has(permissionId))
}

function isRemoved(permissionId: string): boolean {
  return baselineSet.value.has(permissionId) && !draftSet.value.has(permissionId)
}

function isAdded(permissionId: string): boolean {
  return !baselineSet.value.has(permissionId) && draftSet.value.has(permissionId)
}

function markAll(ids: string[], assigned: boolean) {
  const set = new Set(draftIds.value)
  for (const id of ids) {
    if (assigned) set.add(id)
    else set.delete(id)
  }
  draftIds.value = [...set]
}

function visibleIds(): string[] {
  return filteredRows.value.map((r) => r.permission.id)
}

function markAllVisible() {
  markAll(visibleIds(), true)
}

function unmarkAllVisible() {
  markAll(visibleIds(), false)
}

function markApp(app: string, assigned: boolean) {
  const ids = filteredRows.value
    .filter((r) => r.app === app)
    .map((r) => r.permission.id)
  markAll(ids, assigned)
}

function markResource(app: string, tela: string, assigned: boolean) {
  const ids = filteredRows.value
    .filter((r) => r.app === app && r.tela === tela)
    .map((r) => r.permission.id)
  markAll(ids, assigned)
}

function isAppCollapsed(app: string): boolean {
  return collapsedApps.value.has(app)
}

function isGroupCollapsed(key: string): boolean {
  return collapsedGroups.value.has(key)
}

function toggleApp(app: string) {
  const next = new Set(collapsedApps.value)
  if (next.has(app)) next.delete(app)
  else next.add(app)
  collapsedApps.value = next
}

function toggleGroup(key: string) {
  const next = new Set(collapsedGroups.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  collapsedGroups.value = next
}

function groupAssignedCount(rows: PermissionRow[]): number {
  return rows.filter((r) => r.assigned).length
}

function toggleCompareRole(roleId: string) {
  if (compareRoleIds.value.includes(roleId)) {
    compareRoleIds.value = compareRoleIds.value.filter((id) => id !== roleId)
    if (compareRoleIds.value.length === 0 && viewFilter.value === 'differences') {
      viewFilter.value = 'all'
    }
    return
  }
  if (compareRoleIds.value.length >= MAX_COMPARE) {
    $q.notify({
      type: 'warning',
      message: `Maximum of ${MAX_COMPARE} comparison columns`,
    })
    return
  }
  compareRoleIds.value = [...compareRoleIds.value, roleId]
}

function addCompareRole(roleId: string) {
  toggleCompareRole(roleId)
}

function copyFromRole(role: RoleResponse) {
  draftIds.value = [...role.permission_ids]
  copyMenuOpen.value = false
  $q.notify({
    type: 'info',
    message: `Permissions copied from ${formatRoleLabel(role.name)}`,
  })
}

function close() {
  if (!isDirty.value) {
    open.value = false
    return
  }
  $q.dialog({
    title: 'Pending changes',
    message: 'Discard unsaved changes?',
    cancel: { flat: true, label: 'Keep editing', color: 'primary' },
    ok: { unelevated: true, label: 'Discard', color: 'negative' },
    persistent: true,
  }).onOk(() => {
    open.value = false
  })
}

function save() {
  emit('save', [...draftIds.value])
}

function printMatrix() {
  window.print()
}
</script>

<template>
  <q-dialog
    v-model="open"
    persistent
    transition-show="fade"
    transition-hide="fade"
    class="assign-perms-dialog"
  >
    <q-card
      v-if="role"
      flat
      class="assign-perms"
    >
      <header class="assign-perms__titlebar">
        <h2 class="assign-perms__title">
          Permissions — {{ roleDisplayName }}
        </h2>
        <button
          type="button"
          class="assign-perms__close-x"
          aria-label="Close"
          @click="close"
        >
          <q-icon
            name="close"
            size="18px"
          />
        </button>
      </header>

      <section class="assign-perms__hero">
        <div class="assign-perms__role">
          <div class="assign-perms__shield">
            <q-icon
              name="verified_user"
              size="18px"
            />
          </div>
          <div>
            <div class="assign-perms__role-name">{{ roleDisplayName }}</div>
            <div class="assign-perms__role-slug">{{ roleSlug }}</div>
          </div>
        </div>

        <div class="assign-perms__hero-actions">
          <button
            type="button"
            class="assign-perms__btn assign-perms__btn--ghost"
            @click="printMatrix"
          >
            <q-icon
              name="print"
              size="14px"
            />
            Print
          </button>
          <button
            type="button"
            class="assign-perms__btn assign-perms__btn--primary"
            @click="markAllVisible"
          >
            <q-icon
              name="done_all"
              size="14px"
            />
            Select all
          </button>
          <button
            type="button"
            class="assign-perms__btn assign-perms__btn--warn"
            @click="unmarkAllVisible"
          >
            <q-icon
              name="remove_done"
              size="14px"
            />
            Clear all
          </button>
          <button
            type="button"
            class="assign-perms__btn assign-perms__btn--muted"
            :disabled="otherRoles.length === 0"
          >
            <q-icon
              name="content_copy"
              size="14px"
            />
            Copy from another role...
            <q-menu
              v-model="copyMenuOpen"
              anchor="bottom right"
              self="top right"
            >
              <q-list
                dense
                style="min-width: 220px"
              >
                <q-item
                  v-for="source in otherRoles"
                  :key="source.id"
                  v-close-popup
                  clickable
                  @click="copyFromRole(source)"
                >
                  <q-item-section>
                    <q-item-label>{{ formatRoleLabel(source.name) }}</q-item-label>
                    <q-item-label caption>
                      {{ source.permission_ids.length }} permissions
                    </q-item-label>
                  </q-item-section>
                </q-item>
              </q-list>
            </q-menu>
          </button>
          <div class="assign-perms__assigned-count">
            <q-icon
              name="check_circle"
              size="14px"
            />
            <span>{{ assignedCount }} assigned</span>
          </div>
        </div>
      </section>

      <section class="assign-perms__toolbar">
        <div class="assign-perms__toolbar-row">
          <label class="assign-perms__search">
            <q-icon
              name="search"
              size="16px"
              class="assign-perms__search-icon"
            />
            <input
              v-model="search"
              type="search"
              placeholder="Search by name or key..."
            >
          </label>

          <div class="assign-perms__select-wrap">
            <q-select
              v-model="appFilter"
              :options="appOptions"
              dense
              borderless
              clearable
              emit-value
              map-options
              dropdown-icon="expand_more"
              :display-value="appFilter ?? 'All services'"
              class="assign-perms__app-filter"
            />
          </div>

          <div class="assign-perms__view-toggle">
            <button
              type="button"
              :class="{ 'is-active': viewFilter === 'all' }"
              @click="viewFilter = 'all'"
            >
              All
            </button>
            <button
              type="button"
              :class="{ 'is-active': viewFilter === 'assigned' }"
              @click="viewFilter = 'assigned'"
            >
              Assigned
            </button>
            <button
              type="button"
              :class="{ 'is-active': viewFilter === 'unassigned' }"
              @click="viewFilter = 'unassigned'"
            >
              Unassigned
            </button>
            <button
              type="button"
              :class="{ 'is-active': viewFilter === 'differences' }"
              :disabled="compareRoles.length === 0"
              :title="compareRoles.length === 0 ? 'Select at least one role in Compare with' : undefined"
              @click="viewFilter = 'differences'"
            >
              Differences
            </button>
          </div>
        </div>

        <div class="assign-perms__compare-row">
          <span class="assign-perms__compare-label">Compare with:</span>
          <div class="assign-perms__compare-chips">
            <button
              v-for="cmp in compareRoles"
              :key="cmp.id"
              type="button"
              class="assign-perms__chip"
              @click="toggleCompareRole(cmp.id)"
            >
              <q-icon
                name="check"
                size="14px"
              />
              {{ formatRoleLabel(cmp.name) }}
            </button>
            <button
              v-if="availableCompareRoles.length && compareRoleIds.length < MAX_COMPARE"
              type="button"
              class="assign-perms__chip-add"
            >
              + {{ formatRoleLabel(availableCompareRoles[0]!.name) }}
              <q-menu>
                <q-list dense>
                  <q-item
                    v-for="opt in availableCompareRoles"
                    :key="opt.id"
                    v-close-popup
                    clickable
                    @click="addCompareRole(opt.id)"
                  >
                    <q-item-section>{{ formatRoleLabel(opt.name) }}</q-item-section>
                  </q-item>
                </q-list>
              </q-menu>
            </button>
          </div>
          <span class="assign-perms__compare-count">
            {{ compareRoles.length }}/{{ MAX_COMPARE }} columns
          </span>
        </div>
      </section>

      <section class="assign-perms__matrix-wrap">
        <table class="assign-perms__matrix">
          <thead>
            <tr>
              <th class="assign-perms__th-tela">Screen</th>
              <th class="assign-perms__th-perm">Permission</th>
              <th class="assign-perms__th-target">
                <div class="assign-perms__th-kicker">Target</div>
                <div class="assign-perms__th-name">{{ roleDisplayName }}</div>
              </th>
              <th
                v-for="cmp in compareRoles"
                :key="cmp.id"
                class="assign-perms__th-compare"
              >
                <div class="assign-perms__th-name">
                  {{ formatRoleLabel(cmp.name) }}
                </div>
                <div class="assign-perms__th-slug">
                  {{ cmp.name }}
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <template
              v-for="appGroup in grouped"
              :key="appGroup.app"
            >
              <tr class="assign-perms__app-bar">
                <td :colspan="3 + compareRoles.length">
                  <div class="assign-perms__app-head">
                    <button
                      type="button"
                      class="assign-perms__toggle"
                      :aria-expanded="!isAppCollapsed(appGroup.app)"
                      :title="isAppCollapsed(appGroup.app) ? 'Expand app' : 'Collapse app'"
                      @click="toggleApp(appGroup.app)"
                    >
                      <q-icon
                        :name="isAppCollapsed(appGroup.app) ? 'chevron_right' : 'expand_more'"
                        size="18px"
                      />
                      <span class="assign-perms__toggle-label">{{ appGroup.app }}</span>
                      <span class="assign-perms__toggle-count">
                        {{ appGroup.rowCount }} permissions
                      </span>
                    </button>
                    <div class="assign-perms__app-actions">
                      <button
                        type="button"
                        class="assign-perms__link"
                        @click="markApp(appGroup.app, true)"
                      >
                        <span class="assign-perms__box assign-perms__box--on" />
                        Select app
                      </button>
                      <button
                        type="button"
                        class="assign-perms__link"
                        @click="markApp(appGroup.app, false)"
                      >
                        <span class="assign-perms__box" />
                        Clear app
                      </button>
                    </div>
                  </div>
                </td>
              </tr>

              <template v-if="!isAppCollapsed(appGroup.app)">
                <template
                  v-for="resource in appGroup.resources"
                  :key="resource.key"
                >
                  <tr class="assign-perms__resource-bar">
                    <td :colspan="3 + compareRoles.length">
                      <div class="assign-perms__resource-head">
                        <button
                          type="button"
                          class="assign-perms__toggle"
                          :aria-expanded="!isGroupCollapsed(resource.key)"
                          :title="isGroupCollapsed(resource.key) ? 'Expand group' : 'Collapse group'"
                          @click="toggleGroup(resource.key)"
                        >
                          <q-icon
                            :name="isGroupCollapsed(resource.key) ? 'chevron_right' : 'expand_more'"
                            size="18px"
                          />
                          <strong>{{ resource.app }} &gt; {{ resource.tela }}</strong>
                          <span class="assign-perms__toggle-count">
                            {{ groupAssignedCount(resource.rows) }}/{{ resource.rows.length }}
                          </span>
                        </button>
                        <div class="assign-perms__resource-actions">
                          <label
                            class="assign-perms__mini-check"
                            @click.stop
                          >
                            <input
                              type="checkbox"
                              :checked="resource.rows.length > 0 && resource.rows.every((r) => r.assigned)"
                              @change="markResource(resource.app, resource.tela, true)"
                            >
                            Select all
                          </label>
                          <label
                            class="assign-perms__mini-check"
                            @click.stop
                          >
                            <input
                              type="checkbox"
                              :checked="resource.rows.length > 0 && resource.rows.every((r) => !r.assigned)"
                              @change="markResource(resource.app, resource.tela, false)"
                            >
                            Clear all
                          </label>
                        </div>
                      </div>
                    </td>
                  </tr>

                  <tr
                    v-for="row in resource.rows"
                    v-show="!isGroupCollapsed(resource.key)"
                    :key="row.permission.id"
                    class="assign-perms__row"
                  >
                    <td class="assign-perms__td-tela">{{ row.tela }}</td>
                    <td class="assign-perms__td-perm">
                      <div class="assign-perms__perm">
                        <q-icon
                          :name="row.icon"
                          size="16px"
                          class="assign-perms__perm-icon"
                        />
                        <div>
                          <div class="assign-perms__perm-name">
                            <span>{{ row.permission.name }}</span>
                            <span
                              v-if="row.critical"
                              class="assign-perms__critical"
                            >Critical</span>
                            <span
                              v-if="isRemoved(row.permission.id)"
                              class="assign-perms__removed"
                            >Removed</span>
                            <span
                              v-else-if="isAdded(row.permission.id)"
                              class="assign-perms__modified"
                            >Modified</span>
                          </div>
                          <div class="assign-perms__perm-code">
                            {{ row.permission.code }}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td class="assign-perms__td-target">
                      <button
                        type="button"
                        class="assign-perms__yn"
                        :class="[
                          row.assigned ? 'assign-perms__yn--yes' : 'assign-perms__yn--no',
                          {
                            'assign-perms__yn--added': isAdded(row.permission.id),
                            'assign-perms__yn--removed': isRemoved(row.permission.id),
                          },
                        ]"
                        :title="row.assigned ? 'Assigned' : 'Unassigned'"
                        :aria-label="row.assigned ? 'Assigned — click to remove' : 'Unassigned — click to assign'"
                        @click="toggleAssigned(row.permission.id)"
                      >
                        <q-icon
                          v-if="row.assigned || isRemoved(row.permission.id)"
                          :name="isRemoved(row.permission.id) ? 'close' : 'check'"
                          size="18px"
                        />
                      </button>
                    </td>
                    <td
                      v-for="cmp in row.compare"
                      :key="cmp.roleId"
                      class="assign-perms__td-compare"
                    >
                      <span
                        class="assign-perms__yn assign-perms__yn--readonly"
                        :class="cmp.assigned ? 'assign-perms__yn--yes' : 'assign-perms__yn--no'"
                        :title="cmp.assigned ? 'Assigned' : 'Unassigned'"
                      >
                        <q-icon
                          v-if="cmp.assigned"
                          name="check"
                          size="18px"
                        />
                      </span>
                    </td>
                  </tr>
                </template>
              </template>
            </template>

            <tr v-if="grouped.length === 0">
              <td
                :colspan="3 + compareRoles.length"
                class="assign-perms__empty"
              >
                No permissions found with the current filters.
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <footer class="assign-perms__footer">
        <div
          class="assign-perms__footer-status"
          :class="{ 'assign-perms__footer-status--dirty': isDirty }"
        >
          {{ footerStatus }}
        </div>
        <div class="assign-perms__footer-actions">
          <button
            v-if="isDirty"
            type="button"
            class="assign-perms__btn assign-perms__btn--primary"
            :disabled="saving"
            @click="save"
          >
            Save
          </button>
          <button
            type="button"
            class="assign-perms__btn assign-perms__btn--ghost"
            @click="close"
          >
            <q-icon
              name="close"
              size="14px"
            />
            Close
          </button>
        </div>
      </footer>
    </q-card>
  </q-dialog>
</template>

<style lang="scss">
.assign-perms-dialog {
  .q-dialog__inner {
    padding: 0.75rem;
    max-width: none !important;
    width: 100%;
  }

  .q-dialog__inner > div {
    max-width: none !important;
  }

  .q-dialog__backdrop {
    background: rgba(15, 23, 42, 0.45);
  }
}
</style>

<style scoped lang="scss">
.assign-perms {
  --ap-ink: #0f172a;
  --ap-muted: #64748b;
  --ap-line: #e2e8f0;
  --ap-soft: #f8fafc;
  --ap-soft-2: #f1f5f9;
  --ap-blue: #2563eb;
  --ap-blue-soft: #dbeafe;
  --ap-target: #eef2ff;
  --ap-orange: #f97316;
  --ap-cyan: #ecfeff;
  --ap-cyan-ink: #0e7490;

  display: flex;
  flex-direction: column;
  width: min(1100px, calc(100vw - 1.5rem));
  /* Fixed height so filters/collapse don't resize the dialog shell. */
  height: calc(100vh - 1.5rem);
  max-height: calc(100vh - 1.5rem);
  border-radius: 12px;
  background: #fff;
  color: var(--ap-ink);
  box-shadow:
    0 25px 50px -12px rgba(15, 23, 42, 0.28),
    0 0 0 1px rgba(15, 23, 42, 0.04);
  overflow: hidden;
  font-family:
    Inter,
    ui-sans-serif,
    system-ui,
    -apple-system,
    'Segoe UI',
    Roboto,
    Helvetica,
    Arial,
    sans-serif;
}

.assign-perms__titlebar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.55rem 1rem 0.4rem;
}

.assign-perms__title {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #0b1b33;
  line-height: 1.2;
}

.assign-perms__close-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.7rem;
  height: 1.7rem;
  border: 1px solid var(--ap-line);
  border-radius: 6px;
  background: #fff;
  color: #475569;
  cursor: pointer;
}

.assign-perms__close-x:hover {
  background: var(--ap-soft);
}

.assign-perms__hero {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.45rem 0.75rem;
  padding: 0.15rem 1rem 0.55rem;
}

.assign-perms__role {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.assign-perms__shield {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 7px;
  background: var(--ap-blue-soft);
  color: var(--ap-blue);
}

.assign-perms__role-name {
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.1;
  color: var(--ap-ink);
}

.assign-perms__role-slug {
  margin-top: 0;
  font-size: 0.7rem;
  line-height: 1.15;
  color: #94a3b8;
}

.assign-perms__hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
}

.assign-perms__btn {
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  height: 1.75rem;
  padding: 0 0.65rem;
  border-radius: 6px;
  border: 1px solid transparent;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: filter 0.12s ease, background 0.12s ease;
}

.assign-perms__btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.assign-perms__btn--ghost {
  background: #fff;
  border-color: var(--ap-line);
  color: #334155;
}

.assign-perms__btn--ghost:hover {
  background: var(--ap-soft);
}

.assign-perms__btn--primary {
  background: var(--ap-blue);
  color: #fff;
}

.assign-perms__btn--primary:hover {
  filter: brightness(1.05);
}

.assign-perms__btn--warn {
  background: var(--ap-orange);
  color: #fff;
}

.assign-perms__btn--warn:hover {
  filter: brightness(1.05);
}

.assign-perms__btn--muted {
  background: var(--ap-soft-2);
  border-color: var(--ap-line);
  color: #475569;
}

.assign-perms__btn--muted:hover:not(:disabled) {
  background: #e2e8f0;
}

.assign-perms__assigned-count {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: 0.15rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: #334155;

  .q-icon {
    color: #16a34a;
  }
}

.assign-perms__toolbar {
  padding: 0.45rem 1rem;
  background: var(--ap-soft);
  border-top: 1px solid var(--ap-line);
  border-bottom: 1px solid var(--ap-line);
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.assign-perms__toolbar-row,
.assign-perms__compare-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.assign-perms__search {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex: 1 1 200px;
  min-width: 180px;
  max-width: 320px;
  height: 1.8rem;
  padding: 0 0.55rem;
  border: 1px solid var(--ap-line);
  border-radius: 6px;
  background: #fff;
}

.assign-perms__search-icon {
  color: #94a3b8;
}

.assign-perms__search input {
  width: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  font-size: 0.78rem;
  color: var(--ap-ink);
}

.assign-perms__search input::placeholder {
  color: #94a3b8;
}

.assign-perms__select-wrap {
  min-width: 130px;
  height: 1.8rem;
  border: 1px solid var(--ap-line);
  border-radius: 6px;
  background: #fff;
  display: flex;
  align-items: center;
  padding: 0 0.15rem 0 0.45rem;
}

.assign-perms__app-filter {
  width: 100%;
  font-size: 0.78rem;
}

.assign-perms__view-toggle {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: 8px;
  background: #e2e8f0;
  margin-left: auto;

  button {
    border: 0;
    background: transparent;
    color: #475569;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.22rem 0.55rem;
    border-radius: 6px;
    cursor: pointer;
    line-height: 1.2;
  }

  button.is-active {
    background: #fff;
    color: var(--ap-ink);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
  }

  button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}

.assign-perms__compare-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #475569;
}

.assign-perms__compare-chips {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
}

.assign-perms__chip {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  height: 1.5rem;
  padding: 0 0.55rem;
  border-radius: 999px;
  border: 1px solid #cbd5e1;
  background: #eef2f7;
  color: #1e293b;
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;

  .q-icon {
    color: var(--ap-blue);
  }
}

.assign-perms__chip-add {
  height: 1.5rem;
  padding: 0 0.45rem;
  border: 0;
  background: transparent;
  color: var(--ap-blue);
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
}

.assign-perms__compare-count {
  font-size: 0.7rem;
  color: var(--ap-muted);
  margin-left: auto;
}

.assign-perms__matrix-wrap {
  flex: 1 1 auto;
  overflow: auto;
  background: #fff;
}

.assign-perms__matrix {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 0.8rem;
}

.assign-perms__matrix thead th {
  position: sticky;
  top: 0;
  z-index: 2;
  background: #fff;
  border-bottom: 1px solid var(--ap-line);
  padding: 0.4rem 0.7rem;
  text-align: left;
  font-size: 0.62rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #94a3b8;
  font-weight: 700;
  line-height: 1.2;
}

.assign-perms__th-tela {
  width: 7.5rem;
}

.assign-perms__th-perm {
  min-width: 16rem;
}

.assign-perms__th-target {
  background: var(--ap-target) !important;
  text-align: center !important;
  min-width: 6.2rem;
  border-left: 1px solid #e0e7ff;
  border-right: 1px solid #e0e7ff;
}

.assign-perms__th-compare {
  text-align: center !important;
  min-width: 6.2rem;
}

.assign-perms__th-kicker {
  font-size: 0.6rem;
  color: #64748b;
  letter-spacing: 0.04em;
  line-height: 1.1;
}

.assign-perms__th-name {
  margin-top: 0;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: none;
  letter-spacing: 0;
  color: #1e293b;
  line-height: 1.15;
}

.assign-perms__th-slug {
  margin-top: 0;
  font-size: 0.6rem;
  font-weight: 600;
  color: #94a3b8;
  letter-spacing: 0.03em;
  line-height: 1.1;
}

.assign-perms__app-bar td {
  background: var(--ap-cyan);
  padding: 0.28rem 0.7rem;
  border-bottom: 1px solid #cffafe;
}

.assign-perms__app-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem 0.75rem;
}

.assign-perms__app-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

.assign-perms__toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.28rem;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  padding: 0;
  min-width: 0;
  text-align: left;
  font: inherit;

  .q-icon {
    flex-shrink: 0;
    color: #64748b;
  }

  strong {
    font-size: 0.76rem;
    line-height: 1.2;
  }
}

.assign-perms__toggle-label {
  font-size: 0.76rem;
  font-weight: 700;
  color: var(--ap-cyan-ink);
}

.assign-perms__toggle-count {
  font-size: 0.68rem;
  font-weight: 600;
  color: #94a3b8;
  margin-left: 0.15rem;
}

.assign-perms__link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  border: 0;
  background: transparent;
  color: var(--ap-cyan-ink);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  line-height: 1.2;
}

.assign-perms__link:hover {
  text-decoration: underline;
}

.assign-perms__box {
  width: 0.8rem;
  height: 0.8rem;
  border: 1.5px solid #67e8f9;
  border-radius: 2px;
  background: #fff;
  display: inline-block;
}

.assign-perms__box--on {
  background: #22d3ee;
  border-color: #0891b2;
  box-shadow: inset 0 0 0 1.5px #fff;
}

.assign-perms__resource-bar td {
  background: var(--ap-soft-2);
  padding: 0.28rem 0.7rem;
  border-bottom: 1px solid var(--ap-line);
}

.assign-perms__resource-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem;
  color: var(--ap-ink);
}

.assign-perms__resource-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
}

.assign-perms__mini-check {
  display: inline-flex;
  align-items: center;
  gap: 0.22rem;
  font-size: 0.7rem;
  color: #475569;
  cursor: pointer;
  line-height: 1.2;

  input {
    width: 0.8rem;
    height: 0.8rem;
    accent-color: var(--ap-blue);
  }
}

.assign-perms__row td {
  padding: 0.28rem 0.7rem;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.assign-perms__td-tela {
  font-weight: 600;
  color: #334155;
  font-size: 0.72rem;
  line-height: 1.2;
}

.assign-perms__perm {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.assign-perms__perm-icon {
  margin-top: 0;
  color: #64748b;
  flex-shrink: 0;
}

.assign-perms__perm-name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.3rem;
  font-weight: 600;
  color: var(--ap-ink);
  font-size: 0.78rem;
  line-height: 1.15;
}

.assign-perms__perm-code {
  margin-top: 0;
  font-size: 0.66rem;
  line-height: 1.15;
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}

.assign-perms__critical {
  display: inline-flex;
  align-items: center;
  padding: 0.02rem 0.32rem;
  border-radius: 999px;
  background: #fee2e2;
  color: #dc2626;
  font-size: 0.6rem;
  font-weight: 700;
  line-height: 1.25;
}

.assign-perms__modified {
  display: inline-flex;
  align-items: center;
  padding: 0.02rem 0.32rem;
  border-radius: 999px;
  background: #fef3c7;
  color: #b45309;
  font-size: 0.6rem;
  font-weight: 700;
  line-height: 1.25;
}

.assign-perms__removed {
  display: inline-flex;
  align-items: center;
  padding: 0.02rem 0.32rem;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 0.6rem;
  font-weight: 700;
  line-height: 1.25;
}

.assign-perms__td-target,
.assign-perms__td-compare {
  text-align: center;
}

.assign-perms__td-target {
  background: rgba(238, 242, 255, 0.55);
  border-left: 1px solid #e0e7ff;
  border-right: 1px solid #e0e7ff;
}

.assign-perms__yn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.55rem;
  height: 1.55rem;
  padding: 0;
  border-radius: 4px;
  border: 1.5px solid #cbd5e1;
  cursor: pointer;
  line-height: 1;
  background: #fff;
}

.assign-perms__yn--yes {
  color: #14532d;
  background: #dcfce7;
  border-color: #14532d;

  .q-icon {
    font-weight: 700;
    -webkit-text-stroke: 0.6px currentColor;
  }
}

.assign-perms__yn--no {
  color: transparent;
  background: #fff;
  border-color: #cbd5e1;
}

.assign-perms__yn--added {
  color: #a16207;
  background: #fef08a;
  border-color: #ca8a04;

  .q-icon {
    -webkit-text-stroke: 0.6px currentColor;
  }
}

.assign-perms__yn--removed {
  color: #b91c1c;
  background: #fee2e2;
  border-color: #dc2626;

  .q-icon {
    -webkit-text-stroke: 0.6px currentColor;
  }
}

button.assign-perms__yn:hover {
  filter: brightness(0.97);
}

button.assign-perms__yn--yes:hover {
  color: #14532d;
  border-color: #14532d;
  background: #bbf7d0;
}

button.assign-perms__yn--no:hover {
  border-color: #94a3b8;
  background: #f8fafc;
}

button.assign-perms__yn--added:hover {
  color: #854d0e;
  border-color: #a16207;
  background: #fde047;
}

button.assign-perms__yn--removed:hover {
  color: #991b1b;
  border-color: #b91c1c;
  background: #fecaca;
}

.assign-perms__yn--readonly {
  cursor: default;
}

.assign-perms__empty {
  padding: 1.5rem 1rem !important;
  text-align: center;
  color: #94a3b8;
}

.assign-perms__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: 0.45rem 1rem;
  border-top: 1px solid var(--ap-line);
  background: #fff;
}

.assign-perms__footer-status {
  font-size: 0.75rem;
  color: var(--ap-muted);
}

.assign-perms__footer-status--dirty {
  color: #c2410c;
  font-weight: 600;
}

.assign-perms__footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.35rem;
}

@media print {
  .assign-perms__titlebar .assign-perms__close-x,
  .assign-perms__hero-actions,
  .assign-perms__toolbar,
  .assign-perms__footer,
  .assign-perms__app-actions,
  .assign-perms__resource-actions {
    display: none !important;
  }

  .assign-perms {
    width: 100%;
    height: auto;
    box-shadow: none;
    border-radius: 0;
  }

  .assign-perms__matrix-wrap {
    overflow: visible;
  }
}
</style>
