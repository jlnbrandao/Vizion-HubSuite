import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { navigationApi } from '@/services/api'
import type { NavigationItemResponse } from '@/types/api'

/**
 * Shell menu. The backend already applied entitlement + RBAC filtering, so the
 * frontend only decides ordering, grouping and the active entry.
 */
export const useNavigationStore = defineStore('navigation', () => {
  const items = ref<NavigationItemResponse[]>([])
  const services = ref<string[]>([])
  const homeRoute = ref('/dashboard')
  const loading = ref(false)
  const loaded = ref(false)

  const quickItems = computed(() => items.value.filter((item) => item.quick))

  async function load() {
    loading.value = true
    try {
      const { data } = await navigationApi.get()
      items.value = data.items
      services.value = data.services
      homeRoute.value = data.home_route
      loaded.value = true
    } catch {
      items.value = []
      services.value = []
    } finally {
      loading.value = false
    }
  }

  /** Loads once per session; call `load()` to force a refresh after a role change. */
  async function ensureLoaded() {
    if (loaded.value || loading.value) return
    await load()
  }

  function clear() {
    items.value = []
    services.value = []
    homeRoute.value = '/dashboard'
    loaded.value = false
  }

  return {
    items,
    services,
    homeRoute,
    loading,
    loaded,
    quickItems,
    load,
    ensureLoaded,
    clear,
  }
})
