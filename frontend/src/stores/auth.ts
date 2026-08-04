import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi, dashboardApi, tokenStorage } from '@/services/api'
import type { AuthUser } from '@/types/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const accessToken = ref<string | null>(tokenStorage.getAccess())
  const bootstrapped = ref(false)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(
    () => Boolean(accessToken.value && user.value),
  )

  function persistTokens(access: string, refresh: string) {
    tokenStorage.set(access, refresh)
    accessToken.value = access
  }

  function clearSession() {
    tokenStorage.clear()
    accessToken.value = null
    user.value = null
  }

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await authApi.login(email, password)
      persistTokens(data.access_token, data.refresh_token)

      // Minimal identity from login response — ensures isAuthenticated before hydrate.
      user.value = {
        id: data.user_id,
        email: data.email,
        fullName: data.full_name,
        roleNames: [],
        permissions: [],
      }

      try {
        await hydrateFromDashboard()
      } catch {
        // Token is valid; permissions can be loaded after navigation.
      }

      bootstrapped.value = true
    } catch {
      error.value = 'Credenciais inválidas'
      clearSession()
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
    const existing = tokenStorage.getAccess()
    if (!existing) {
      accessToken.value = null
      user.value = null
      bootstrapped.value = true
      return
    }

    accessToken.value = existing
    try {
      await hydrateFromDashboard()
    } catch {
      clearSession()
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
      clearSession()
    }
  }

  return {
    user,
    accessToken,
    bootstrapped,
    loading,
    error,
    isAuthenticated,
    login,
    logout,
    bootstrap,
    hydrateFromDashboard,
    clearSession,
  }
})
