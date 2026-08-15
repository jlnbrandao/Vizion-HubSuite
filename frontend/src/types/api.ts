export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user_id: string | null
  email: string
  full_name: string
  mfa_required?: boolean
  mfa_token?: string | null
}

export interface DashboardWidget {
  id: string
  title: string
  widget_type: string
  data: Record<string, unknown>
}

export interface DashboardResponse {
  user_id: string
  email: string
  full_name: string
  tenant_id?: string | null
  tenant_slug?: string
  tenant_name?: string
  role_names: string[]
  permissions: string[]
  widgets: DashboardWidget[]
}

/** GET /navigation — menu already filtered by entitlement + RBAC. */
export interface NavigationItemResponse {
  id: string
  label: string
  icon: string
  route: string
  group: string
  service?: string | null
  permission?: string | null
  quick: boolean
}

export interface NavigationResponse {
  home_route: string
  services: string[]
  items: NavigationItemResponse[]
}

/** Service catalog — what the Hub offers and what a tenant has contracted. */
export interface ServiceResponse {
  slug: string
  namespace: string
  name: string
  description: string
  version: string
  is_core: boolean
  is_active: boolean
}

export interface TenantServiceResponse extends ServiceResponse {
  status: string | null
  plan: string | null
  entitled: boolean
  quotas: Record<string, unknown>
  expires_at?: string | null
}

export interface SetTenantServicePayload {
  status: string
  plan?: string | null
  quotas?: Record<string, unknown> | null
  expires_at?: string | null
}

/** Metering — what a tenant consumed per service, metric and period. */
export interface UsageRecordResponse {
  service: string
  metric: string
  granularity: 'day' | 'month'
  period_start: string
  quantity: number
}

export interface UsageReportResponse {
  tenant_id: string
  since: string
  until: string
  totals_by_service: Record<string, number>
  records: UsageRecordResponse[]
}

export interface UsageQuery {
  since?: string
  until?: string
  service?: string
  granularity?: 'day' | 'month'
}

/** GET /auth/me — identity and effective access (no longer carried in the JWT). */
export interface MeResponse {
  id: string
  email: string
  full_name: string
  tenant_id: string
  tenant_slug: string
  tenant_name?: string
  role_names: string[]
  permissions: string[]
  services: string[]
}

export interface AuthUser {
  id: string
  email: string
  fullName: string
  tenantId?: string | null
  tenantSlug?: string
  tenantName?: string
  roleNames: string[]
  permissions: string[]
  /** Services the tenant is entitled to; gates whole frontend modules. */
  services: string[]
}

export interface UserResponse {
  id: string
  email: string
  username: string
  full_name: string
  role_ids: string[]
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface CreateUserPayload {
  email: string
  username: string
  full_name: string
  password: string
  role_ids: string[]
}

export interface UpdateUserPayload {
  username: string
  full_name: string
  is_active: boolean
}

export interface ChangePasswordPayload {
  new_password: string
}

export interface RoleResponse {
  id: string
  name: string
  description: string
  permission_ids: string[]
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

export interface CreateRolePayload {
  name: string
  description: string
}

export interface UpdateRolePayload {
  description: string
  is_active: boolean
}

export interface PermissionResponse {
  id: string
  code: string
  legacy_code: string | null
  service: string | null
  resource: string
  action: string
  name: string
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PermissionCatalogEntryResponse {
  code: string
  legacy_code: string
  service: string
  resource: string
  action: string
  name: string
  description: string
}

export interface PermissionBundleResponse {
  id: string
  slug: string
  service: string
  name: string
  description: string
  is_active: boolean
  permission_ids: string[]
  permission_codes: string[]
}

export interface UpsertPermissionBundlePayload {
  slug: string
  service: string
  name: string
  description: string
  permission_ids: string[]
}

export interface CreatePermissionPayload {
  code: string
  name: string
  description: string
}

export interface UpdatePermissionPayload {
  name: string
  description: string
  is_active: boolean
}

export interface IdResponse {
  id: string
}

export interface TenantAdminResponse {
  id: string
  username: string
  email: string
  full_name: string
}

export interface TenantResponse {
  id: string
  slug: string
  name: string
  is_active: boolean
  admin: TenantAdminResponse | null
}

export interface CreateTenantPayload {
  slug: string
  name: string
  admin_username: string
  admin_email: string
  admin_full_name: string
  admin_password: string
}


export interface RenameTenantPayload {
  name: string
}

