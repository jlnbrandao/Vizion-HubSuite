<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import AccountModal from '@/components/layout/AccountModal.vue'
import type { NavMenuOption } from '@/composables/useLayoutConfig'

const props = withDefaults(
  defineProps<{
    headerTitle?: string
    userSubtitle?: string
    navMenuOptions?: NavMenuOption[]
  }>(),
  {
    headerTitle: 'Lanstar',
    userSubtitle: '',
    navMenuOptions: () => [],
  },
)

const emit = defineEmits<{
  toggleDrawer: []
}>()

const $q = useQuasar()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const showAccountModal = ref(false)
const navMenuSelected = ref<string | null>(null)

const isMediumOrLargeScreen = computed(() => $q.screen.gt.sm)

const selectableOptions = computed(() => {
  const current = navMenuSelected.value
  return props.navMenuOptions.filter((opt) => opt.value !== current)
})

const selectedNavMenuLabel = computed(() => {
  const current = props.navMenuOptions.find((opt) => opt.value === navMenuSelected.value)
  return current?.label || props.headerTitle
})

function syncSelectionFromRoute() {
  const path = route.path.replace(/\/$/, '') || '/'
  const ranked = [...props.navMenuOptions].sort(
    (a, b) => b.path.length - a.path.length,
  )
  const match = ranked.find((opt) => {
    if (opt.path === '/dashboard') {
      return path === '/dashboard' || path === '/'
    }
    return path === opt.path || path.startsWith(`${opt.path}/`)
  })
  navMenuSelected.value = match?.value ?? null
}

watch(
  () => [route.fullPath, props.navMenuOptions] as const,
  () => {
    syncSelectionFromRoute()
  },
  { immediate: true, deep: true },
)

function toggleLeftDrawer() {
  emit('toggleDrawer')
}

function handleNavMenuSelect(value: string) {
  navMenuSelected.value = value
  const option = props.navMenuOptions.find((opt) => opt.value === value)
  if (option) {
    void router.push(option.path)
  }
}
</script>

<template>
  <q-header class="base-header">
    <q-toolbar class="base-header__toolbar">
      <div class="base-header__left">
        <q-btn
          flat
          round
          icon="menu"
          class="base-header__icon-btn"
          aria-label="Open menu"
          @click="toggleLeftDrawer"
        />

        <q-select
          v-model="navMenuSelected"
          :options="selectableOptions"
          option-value="value"
          option-label="label"
          emit-value
          map-options
          borderless
          dense
          class="base-header__nav-select"
          @update:model-value="handleNavMenuSelect"
        >
          <template #selected>
            <span class="base-header__title">
              {{ selectedNavMenuLabel }}
            </span>
          </template>
          <template #option="scope">
            <q-item
              v-bind="scope.itemProps"
              class="base-header__nav-option"
            >
              <q-item-section avatar>
                <q-icon
                  :name="scope.opt.icon"
                  size="20px"
                />
              </q-item-section>
              <q-item-section>
                <q-item-label>{{ scope.opt.label }}</q-item-label>
              </q-item-section>
            </q-item>
          </template>
        </q-select>
      </div>

      <div
        v-if="isMediumOrLargeScreen"
        class="base-header__right"
      >
        <q-btn
          flat
          round
          icon="notifications_none"
          class="base-header__icon-btn"
          aria-label="Notifications"
        >
          <q-tooltip>Notifications (demo)</q-tooltip>
        </q-btn>

        <q-btn
          flat
          round
          icon="help_outline"
          class="base-header__icon-btn"
          aria-label="Help"
        >
          <q-tooltip>Help (demo)</q-tooltip>
        </q-btn>

        <button
          type="button"
          class="base-header__user"
          @click="showAccountModal = true"
        >
          <div class="base-header__user-text">
            <span>{{ auth.user?.fullName || 'User' }}</span>
            <small v-if="userSubtitle || auth.user?.email">
              {{ userSubtitle || auth.user?.email }}
            </small>
          </div>
          <q-icon
            name="account_circle"
            size="28px"
          />
        </button>
      </div>
    </q-toolbar>

    <AccountModal v-model="showAccountModal" />
  </q-header>
</template>

<style scoped lang="scss">
.base-header {
  background: var(--app-navigation-background, #f9fafb);
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
  color: #111827;
}

.base-header__toolbar {
  min-height: 56px;
  padding: 0 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.base-header__left,
.base-header__right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.base-header__icon-btn {
  color: #4b5563;
}

.base-header__title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  font-family: var(--ls-font-display);
  line-height: 1.2;
}

.base-header__nav-select {
  width: auto !important;
  min-width: 0 !important;
  cursor: pointer;
}

.base-header__nav-select :deep(.q-field__control) {
  height: auto !important;
  min-height: 0 !important;
  padding: 0 !important;
  cursor: pointer !important;
}

.base-header__nav-select :deep(.q-field__native),
.base-header__nav-select :deep(.q-field__marginal) {
  min-height: 0 !important;
  padding: 0 !important;
  height: auto !important;
}

.base-header__nav-select :deep(.q-field__append) {
  padding-left: 0.25rem !important;
}

.base-header__nav-option {
  min-height: 40px;
}

.base-header__user {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.5rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.base-header__user:hover {
  background: #f3f4f6;
}

.base-header__user-text {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-right: 0.25rem;
  line-height: 1.15;
}

.base-header__user-text span {
  font-size: 0.875rem;
  font-weight: 700;
  color: #1f2937;
}

.base-header__user-text small {
  font-size: 0.7rem;
  color: #6b7280;
}

.base-header__user .q-icon {
  color: #4b5563;
}
</style>
