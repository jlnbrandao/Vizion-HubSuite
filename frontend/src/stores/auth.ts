import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios from 'axios'
import { apiErrorMessage, authApi, clearSessionHint, hasSessionHint, tokenStorage } from '@/services/api'
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

  /** Entitlement gate for a whole service slice (menu + routes). */
  function isEntitled(service: string): boolean {
    return user.value?.services.includes(service) ?? false
  }

  function persistAccess(access: string) {
    tokenStorage.setAccess(access)
    accessToken.value = access
  }

  function clearSession() {
    tokenStorage.clear()
    clearSessionHint()
    accessToken.value = null
    user.value = null
  }

  async function login(loginId: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const { data } = await authApi.login(loginId, password)
      if (data.mfa_required && data.mfa_token) {
        sessionStorage.setItem('vizion_mfa_token', data.mfa_token)
        throw new Error('mfa_required')
      }
      persistAccess(data.access_token)

      // Minimal identity from login response — ensures isAuthenticated before hydrate.
      user.value = {
        id: data.user_id || '',
        email: data.email,
        fullName: data.full_name,
        tenantId: null,
        tenantSlug: '',
        tenantName: '',
        roleNames: [],
        permissions: [],
        services: [],
      }

      try {
        await hydrateIdentity()
      } catch {
        // Token is valid; permissions can be loaded after navigation.
      }

      bootstrapped.value = true
    } catch (err) {
      if (err instanceof Error && err.message === 'mfa_required') {
        throw err
      }
      const status = axios.isAxiosError(err) ? err.response?.status : undefined
      error.value =
        status === 401 || status === 403
          ? 'Invalid credentials'
          : apiErrorMessage(err, 'Invalid credentials')
      clearSession()
      throw new Error('login_failed')
    } finally {
      loading.value = false
    }
  }

  function setSession(payload: {
    accessToken: string
    user: {
      id: string
      email: string
      full_name: string
      permissions: string[]
    }
  }) {
    persistAccess(payload.accessToken)
    user.value = {
      id: payload.user.id,
      email: payload.user.email,
      fullName: payload.user.full_name,
      tenantId: null,
      tenantSlug: '',
      tenantName: '',
      roleNames: [],
      permissions: payload.user.permissions,
      services: [],
    }
  }

  /** Identity + effective access. The JWT carries none of this. */
  async function hydrateIdentity() {
    const { data } = await authApi.me()
    user.value = {
      id: data.id,
      email: data.email,
      fullName: data.full_name,
      tenantId: data.tenant_id ?? null,
      tenantSlug: data.tenant_slug ?? '',
      tenantName: data.tenant_name ?? '',
      roleNames: data.role_names,
      permissions: data.permissions,
      services: data.services ?? [],
    }
  }

  async function bootstrap() {
    tokenStorage.clear()
    if (!hasSessionHint()) {
      bootstrapped.value = true
      return
    }
    try {
      const { data } = await authApi.refresh()
      persistAccess(data.access_token)
      await hydrateIdentity()
    } catch {
      clearSession()
    } finally {
      bootstrapped.value = true
    }
  }

  async function logout() {
    try {
      await authApi.logout()
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
    isEntitled,
    login,
    logout,
    bootstrap,
    hydrateIdentity,
    clearSession,
    setSession,
  }
})
