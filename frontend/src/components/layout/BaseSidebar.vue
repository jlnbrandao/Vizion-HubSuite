<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import logoColor from '@/assets/brand/hub-color.png'

export interface MenuItem {
  id: string
  divider?: boolean
  label?: string
  icon?: string
  active?: boolean
  link?: string
  required_permission?: string
}

defineProps<{
  menuItems: MenuItem[]
}>()

const emit = defineEmits<{
  menuClick: [item: MenuItem]
  logout: []
}>()

const router = useRouter()
const $q = useQuasar()
const drawerOpen = defineModel<boolean>('drawerOpen', { required: true })

const isSmallScreen = computed(() => $q.screen.lt.md)

function handleMenuClick(item: MenuItem) {
  if (item.divider) return

  if (item.link) {
    void router.push(item.link)
    if (isSmallScreen.value) {
      drawerOpen.value = false
    }
  }

  emit('menuClick', item)
}

function handleLogout() {
  emit('logout')
}
</script>

<template>
  <q-drawer
    v-model="drawerOpen"
    :width="260"
    class="base-sidebar"
  >
    <div class="base-sidebar__inner">
      <div class="base-sidebar__logo">
        <img
          :src="logoColor"
          alt="Vizion"
        >
      </div>

      <div class="base-sidebar__menu">
        <template
          v-for="item in menuItems"
          :key="item.id"
        >
          <div
            v-if="item.divider"
            class="base-sidebar__divider"
            role="separator"
          />
          <button
            v-else
            type="button"
            class="base-sidebar__item"
            :class="{ 'base-sidebar__item--active': item.active }"
            @click="handleMenuClick(item)"
          >
            <q-icon
              :name="item.icon || 'chevron_right'"
              size="20px"
            />
            <span>{{ item.label }}</span>
          </button>
        </template>
      </div>

      <div
        v-if="isSmallScreen"
        class="base-sidebar__mobile"
      >
        <button
          type="button"
          class="base-sidebar__item"
          @click="handleLogout"
        >
          <q-icon
            name="logout"
            size="20px"
          />
          <span>Sign out</span>
        </button>
      </div>
    </div>
  </q-drawer>
</template>

<style scoped lang="scss">
.base-sidebar {
  background-color: var(--app-navigation-background, #f9fafb);
  border-right: none !important;
}

.base-sidebar :deep(.q-drawer__content) {
  border-right: none !important;
  background-color: var(--app-navigation-background, #f9fafb);
}

.base-sidebar__inner {
  padding: 1rem;
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background-color: var(--app-navigation-background, #f9fafb);
}

.base-sidebar__logo {
  padding-top: 1.25rem;
  margin-bottom: 1rem;
  width: 100%;
  overflow: hidden;
  background: transparent;
}

.base-sidebar__logo img {
  display: block;
  width: 100%;
  height: auto;
  object-fit: contain;
}

.base-sidebar__menu {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.base-sidebar__divider {
  margin: 0.5rem 0.25rem;
  border-top: 1px solid #e5e7eb;
}

.base-sidebar__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem;
  border: 0;
  border-radius: 0.5rem;
  background: transparent;
  color: #4b5563;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  position: relative;
}

.base-sidebar__item:hover {
  background: #f3f4f6;
}

.base-sidebar__item--active {
  background: var(--app-content-background, #ffffff);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
  color: #111827;
  font-weight: 500;
}

.base-sidebar__item--active .q-icon {
  color: var(--q-primary, #1e40af);
}

.base-sidebar__item--active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 24px;
  background-color: var(--q-primary, #1e40af);
  border-radius: 0 4px 4px 0;
}

.base-sidebar__mobile {
  margin-top: auto;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}
</style>
