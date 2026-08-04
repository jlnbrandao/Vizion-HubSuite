import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi } from '@/services/api'
import type { DashboardMenuItem, DashboardWidget } from '@/types/api'

/**
 * Dashboard content comes from the backend composer.
 * Frontend does NOT branch on role names — it renders menu/widgets as returned.
 */
export const useDashboardStore = defineStore('dashboard', () => {
  const menu = ref<DashboardMenuItem[]>([])
  const widgets = ref<DashboardWidget[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const { data } = await dashboardApi.get()
      menu.value = data.menu
      widgets.value = data.widgets
    } catch {
      // Fallback for users without dashboard.* (me endpoint still works)
      try {
        const { data } = await dashboardApi.me()
        menu.value = data.menu
        widgets.value = data.widgets
      } catch {
        error.value = 'Não foi possível carregar o dashboard'
        menu.value = []
        widgets.value = []
      }
    } finally {
      loading.value = false
    }
  }

  function clear() {
    menu.value = []
    widgets.value = []
    error.value = null
  }

  return {
    menu,
    widgets,
    loading,
    error,
    load,
    clear,
  }
})
