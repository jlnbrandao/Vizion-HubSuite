<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { PermissionBundleResponse, RoleResponse } from '@/types/api'

const props = defineProps<{
  modelValue: boolean
  role: RoleResponse | null
  bundles: PermissionBundleResponse[]
  selectedIds: string[]
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  save: [groupIds: string[]]
}>()

const open = computed({
  get: () => props.modelValue,
  set: (value: boolean) => emit('update:modelValue', value),
})

const draft = ref<string[]>([])

watch(
  () => [props.modelValue, props.selectedIds] as const,
  ([isOpen, selected]) => {
    if (!isOpen) return
    draft.value = [...selected]
  },
  { immediate: true },
)

const byService = computed(() => {
  const groups = new Map<string, PermissionBundleResponse[]>()
  for (const bundle of props.bundles) {
    const list = groups.get(bundle.service) ?? []
    list.push(bundle)
    groups.set(bundle.service, list)
  }
  return [...groups.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([service, items]) => ({
      service,
      items: [...items].sort((a, b) => a.slug.localeCompare(b.slug)),
    }))
})

const isDirty = computed(() => {
  const before = new Set(props.selectedIds)
  return draft.value.length !== before.size || draft.value.some((id) => !before.has(id))
})

const grantedCodes = computed(() => {
  const selected = new Set(draft.value)
  const codes = new Set<string>()
  for (const bundle of props.bundles) {
    if (!selected.has(bundle.id)) continue
    for (const code of bundle.permission_codes) codes.add(code)
  }
  return codes.size
})

function toggle(bundleId: string) {
  const set = new Set(draft.value)
  if (set.has(bundleId)) set.delete(bundleId)
  else set.add(bundleId)
  draft.value = [...set]
}
</script>

<template>
  <q-dialog
    v-model="open"
    persistent
  >
    <q-card
      v-if="role"
      class="app-page__dialog"
      style="min-width: 520px"
    >
      <q-card-section>
        <div
          class="text-h6"
          style="color: #111827"
        >
          Permission bundles
        </div>
        <div class="app-page__dialog-sub">
          {{ role.name }} — {{ grantedCodes }} permission(s) granted by the selected bundles
        </div>
      </q-card-section>

      <q-card-section class="q-pt-none">
        <div
          v-if="bundles.length === 0"
          class="app-page__muted"
        >
          No bundles available for this tenant.
        </div>

        <div
          v-for="group in byService"
          :key="group.service"
          class="q-mb-md"
        >
          <div class="text-caption text-uppercase text-grey-7 q-mb-xs">
            {{ group.service }}
          </div>
          <q-list
            bordered
            separator
            dense
          >
            <q-item
              v-for="bundle in group.items"
              :key="bundle.id"
              clickable
              @click="toggle(bundle.id)"
            >
              <q-item-section side>
                <q-checkbox
                  :model-value="draft.includes(bundle.id)"
                  color="primary"
                  @update:model-value="toggle(bundle.id)"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ bundle.name }}</q-item-label>
                <q-item-label caption>
                  {{ bundle.slug }} — {{ bundle.permission_codes.length }} permissions
                </q-item-label>
              </q-item-section>
            </q-item>
          </q-list>
        </div>

        <div class="app-page__muted text-caption">
          Bundles add permissions on top of the role's own list; fine-grained
          exceptions still live in Permissions.
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn
          flat
          no-caps
          label="Cancel"
          color="primary"
          @click="open = false"
        />
        <q-btn
          unelevated
          no-caps
          color="primary"
          label="Save"
          :disable="!isDirty"
          :loading="saving"
          @click="emit('save', [...draft])"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>
