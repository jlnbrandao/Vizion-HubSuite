<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import { useAuthStore } from '@/stores/auth'
import { useDashboardStore } from '@/stores/dashboard'
import { useLayoutConfig } from '@/composables/useLayoutConfig'
import BaseHeader from '@/components/layout/BaseHeader.vue'
import BaseSidebar from '@/components/layout/BaseSidebar.vue'
import type { MenuItem } from '@/components/layout/BaseSidebar.vue'

const router = useRouter()
const route = useRoute()
const $q = useQuasar()
const auth = useAuthStore()
const dashboard = useDashboardStore()
const { layoutConfig } = useLayoutConfig()

const isSmartphone = () => window.innerWidth < 768
const leftDrawerOpen = ref(!isSmartphone())

const isDashboardPage = computed(() => {
  const path = route.path.replace(/\/$/, '') || '/'
  return path === '/dashboard' || path === '/'
})

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

function handleMenuClick(_item: MenuItem) {
  // Navigation handled inside BaseSidebar.
}

function handleLogout() {
  $q.dialog({
    title: 'Confirm sign out',
    message: 'Do you want to end this session?',
    cancel: true,
    persistent: false,
  }).onOk(() => {
    void (async () => {
      await auth.logout()
      dashboard.clear()
      await router.push({ name: 'login' })
      $q.notify({ type: 'positive', message: 'Signed out' })
    })()
  })
}

function handleResize() {
  if (isSmartphone() && leftDrawerOpen.value) {
    leftDrawerOpen.value = false
  } else if (!isSmartphone() && !leftDrawerOpen.value) {
    leftDrawerOpen.value = true
  }
}

onMounted(async () => {
  window.addEventListener('resize', handleResize)
  if (!dashboard.menu.length && !dashboard.widgets.length) {
    await dashboard.load()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<template>
  <q-layout
    view="hHh Lpr lFf"
    class="main-layout"
  >
    <BaseHeader
      :header-title="layoutConfig.headerTitle"
      :user-subtitle="layoutConfig.userSubtitle"
      :nav-menu-options="layoutConfig.navMenuOptions"
      @toggle-drawer="toggleLeftDrawer"
    />

    <BaseSidebar
      v-if="!isDashboardPage"
      v-model:drawer-open="leftDrawerOpen"
      :menu-items="layoutConfig.menuItems"
      @menu-click="handleMenuClick"
      @logout="handleLogout"
    />

    <q-page-container class="main-layout__content">
      <router-view :key="route.fullPath" />
    </q-page-container>
  </q-layout>
</template>

<style scoped lang="scss">
.main-layout__content {
  min-height: 100vh;
  background: var(--app-navigation-background, #f9fafb);
}
</style>
