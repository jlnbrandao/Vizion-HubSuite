import { defineStore } from 'pinia'
import { ref } from 'vue'
import { dashboardApi } from '@/services/api'
import type { DashboardWidget } from '@/types/api'

/**
 * Dashboard widgets come from the backend composer.
 * Frontend does NOT branch on role names — it renders widgets as returned.
 * The shell menu is a separate concern: see `stores/navigation`.
 */
export const useDashboardStore = defineStore('dashboard', () => {
  const widgets = ref<DashboardWidget[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load() {
    loading.value = true
    error.value = null
    try {
      const { data } = await dashboardApi.get()
      widgets.value = data.widgets
    } catch {
      // Fallback for users without dashboard.* (me endpoint still works)
      try {
        const { data } = await dashboardApi.me()
        widgets.value = data.widgets
      } catch {
        error.value = 'Could not load the dashboard'
        widgets.value = []
      }
    } finally {
      loading.value = false
    }
  }

  function clear() {
    widgets.value = []
    error.value = null
  }

  return {
    widgets,
    loading,
    error,
    load,
    clear,
  }
})
