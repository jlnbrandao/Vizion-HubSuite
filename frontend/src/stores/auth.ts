import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi, dashboardApi, tokenStorage } from '@/services/api'
import type { AuthUser } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const bootstrapped = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => Boolean(tokenStorage.getAccess() && user.value))

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await authApi.login(email, password)
      tokenStorage.set(data.access_token, data.refresh_token)
      await hydrateFromDashboard()
    } catch {
      error.value = 'Credenciais inválidas'
      tokenStorage.clear()
      user.value = null
      throw new Error('login_failed')
    } finally {
      loading.value = false
    }
  }

  async function hydrateFromDashboard() {
    const { data } = await dashboardApi.me()
    user.value = {
      id: data.user_id,
      email: data.email,
      fullName: data.full_name,
      roleNames: data.role_names,
      permissions: data.permissions,
    }
  }

  async function bootstrap() {
    if (!tokenStorage.getAccess()) {
      bootstrapped.value = true
      return
    }
    try {
      await hydrateFromDashboard()
    } catch {
      tokenStorage.clear()
      user.value = null
    } finally {
      bootstrapped.value = true
    }
  }

  async function logout() {
    const refresh = tokenStorage.getRefresh()
    try {
      if (refresh) {
        await authApi.logout(refresh)
      }
    } finally {
      tokenStorage.clear()
      user.value = null
    }
  }

  return {
    user,
    bootstrapped,
    loading,
    error,
    isAuthenticated,
    login,
    logout,
    bootstrap,
    hydrateFromDashboard,
  }
})
