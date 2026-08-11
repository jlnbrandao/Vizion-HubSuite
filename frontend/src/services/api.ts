import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type {
  ChangePasswordPayload,
  CreatePermissionPayload,
  CreateRolePayload,
  CreateTenantPayload,
  CreateUserPayload,
  DashboardResponse,
  IdResponse,
  PermissionResponse,
  RenameTenantPayload,
  RoleResponse,
  TenantResponse,
  TokenResponse,
  UpdatePermissionPayload,
  UpdateRolePayload,
  UpdateUserPayload,
  UserResponse,
} from '@/types/api'

const LEGACY_ACCESS_KEY = 'lanstar.access_token'
const LEGACY_REFRESH_KEY = 'lanstar.refresh_token'

/** In-memory access token — never persisted (refresh lives in httpOnly cookie). */
let memoryAccessToken: string | null = null

export const tokenStorage = {
  getAccess(): string | null {
    return memoryAccessToken
  },
  setAccess(access: string) {
    memoryAccessToken = access
  },
  clear() {
    memoryAccessToken = null
    try {
      localStorage.removeItem(LEGACY_ACCESS_KEY)
      localStorage.removeItem(LEGACY_REFRESH_KEY)
    } catch {
      // ignore storage access errors
    }
  },
}

export const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
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
  const { data } = await axios.post<TokenResponse>(
    '/api/v1/auth/refresh',
    {},
    { withCredentials: true },
  )
  tokenStorage.setAccess(data.access_token)
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
      try {
        const { useAuthStore } = await import('@/stores/auth')
        useAuthStore().clearSession()
      } catch {
        // Pinia may be unavailable outside the app context.
      }
      return Promise.reject(error)
    }
  },
)

export const authApi = {
  login(login: string, password: string) {
    return api.post<TokenResponse>('/auth/login', { login, password })
  },
  refresh() {
    return api.post<TokenResponse>('/auth/refresh', {})
  },
  logout() {
    return api.post('/auth/logout', {})
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

export function apiErrorMessage(error: unknown, fallback = 'Operation failed'): string {
  if (!axios.isAxiosError(error)) {
    return error instanceof Error ? error.message : fallback
  }
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return detail
      .map((item: { msg?: string }) => item.msg)
      .filter(Boolean)
      .join('; ') || fallback
  }
  return fallback
}

export const usersApi = {
  list(onlyActive = false) {
    return api.get<UserResponse[]>('/users', { params: { only_active: onlyActive } })
  },
  get(userId: string) {
    return api.get<UserResponse>(`/users/${userId}`)
  },
  create(payload: CreateUserPayload) {
    return api.post<IdResponse>('/users', payload)
  },
  update(userId: string, payload: UpdateUserPayload) {
    return api.put(`/users/${userId}`, payload)
  },
  changePassword(userId: string, payload: ChangePasswordPayload) {
    return api.post(`/users/${userId}/change-password`, payload)
  },
  remove(userId: string) {
    return api.delete(`/users/${userId}`)
  },
  replaceRoles(userId: string, roleIds: string[]) {
    return api.put(`/users/${userId}/roles`, { role_ids: roleIds })
  },
}

export const rolesApi = {
  list(onlyActive = false) {
    return api.get<RoleResponse[]>('/roles', { params: { only_active: onlyActive } })
  },
  get(roleId: string) {
    return api.get<RoleResponse>(`/roles/${roleId}`)
  },
  create(payload: CreateRolePayload) {
    return api.post<IdResponse>('/roles', payload)
  },
  update(roleId: string, payload: UpdateRolePayload) {
    return api.put(`/roles/${roleId}`, payload)
  },
  remove(roleId: string) {
    return api.delete(`/roles/${roleId}`)
  },
  replacePermissions(roleId: string, permissionIds: string[]) {
    return api.put(`/roles/${roleId}/permissions`, { permission_ids: permissionIds })
  },
}

export const permissionsApi = {
  list(options: { onlyActive?: boolean; resource?: string; action?: string } = {}) {
    const { onlyActive = false, resource, action } = options
    return api.get<PermissionResponse[]>('/permissions', {
      params: {
        only_active: onlyActive,
        ...(resource ? { resource } : {}),
        ...(action ? { action } : {}),
      },
    })
  },
  get(permissionId: string) {
    return api.get<PermissionResponse>(`/permissions/${permissionId}`)
  },
  create(payload: CreatePermissionPayload) {
    return api.post<IdResponse>('/permissions', payload)
  },
  update(permissionId: string, payload: UpdatePermissionPayload) {
    return api.put(`/permissions/${permissionId}`, payload)
  },
  remove(permissionId: string) {
    return api.delete(`/permissions/${permissionId}`)
  },
}

export const tenantsApi = {
  list(onlyActive = false) {
    return api.get<TenantResponse[]>('/tenants', { params: { only_active: onlyActive } })
  },
  get(tenantId: string) {
    return api.get<TenantResponse>(`/tenants/${tenantId}`)
  },
  create(payload: CreateTenantPayload) {
    return api.post<IdResponse>('/tenants', payload)
  },
  rename(tenantId: string, payload: RenameTenantPayload) {
    return api.put(`/tenants/${tenantId}`, payload)
  },
  activate(tenantId: string) {
    return api.post(`/tenants/${tenantId}/activate`)
  },
  deactivate(tenantId: string) {
    return api.post(`/tenants/${tenantId}/deactivate`)
  },
}
