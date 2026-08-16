import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { createAuthAdapter, loadRuntimeConfig, type AuthPrincipal } from '@openvizion/web-runtime'
import { createHttp, tokenStorage } from '@/http'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthPrincipal | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => Boolean(tokenStorage.get() && user.value))

  async function login(loginId: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const config = await loadRuntimeConfig()
      const http = await createHttp()
      const adapter = createAuthAdapter(config, http)
      const result = await adapter.login(loginId, password)
      tokenStorage.set(result.accessToken)
      user.value = result.user
    } catch {
      error.value = 'Invalid credentials'
      tokenStorage.clear()
      user.value = null
      throw new Error('login_failed')
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    tokenStorage.clear()
    user.value = null
  }

  return { user, loading, error, isAuthenticated, login, logout }
})
