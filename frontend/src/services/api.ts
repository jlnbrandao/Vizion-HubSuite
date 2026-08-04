import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { DashboardResponse, TokenResponse } from '@/types/api'

const ACCESS_KEY = 'lanstar.access_token'
const REFRESH_KEY = 'lanstar.refresh_token'

export const tokenStorage = {
  getAccess(): string | null {
    return localStorage.getItem(ACCESS_KEY)
  },
  getRefresh(): string | null {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.getAccess()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStorage.getRefresh()
  if (!refresh) {
    throw new Error('No refresh token')
  }
  const { data } = await axios.post<TokenResponse>('/api/v1/auth/refresh', {
    refresh_token: refresh,
  })
  tokenStorage.set(data.access_token, data.refresh_token)
  return data.access_token
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config
    if (!original || error.response?.status !== 401) {
      return Promise.reject(error)
    }
    if (original.url?.includes('/auth/login') || original.url?.includes('/auth/refresh')) {
      return Promise.reject(error)
    }

    try {
      refreshPromise ??= refreshAccessToken().finally(() => {
        refreshPromise = null
      })
      const access = await refreshPromise
      original.headers.Authorization = `Bearer ${access}`
      return api(original)
    } catch {
      tokenStorage.clear()
      return Promise.reject(error)
    }
  },
)

export const authApi = {
  login(email: string, password: string) {
    return api.post<TokenResponse>('/auth/login', { email, password })
  },
  logout(refreshToken: string) {
    return api.post('/auth/logout', { refresh_token: refreshToken })
  },
}

export const dashboardApi = {
  get() {
    return api.get<DashboardResponse>('/dashboard')
  },
  me() {
    return api.get<DashboardResponse>('/dashboard/me')
  },
}
