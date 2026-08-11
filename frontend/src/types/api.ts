export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user_id: string
  email: string
  full_name: string
}

export interface DashboardMenuItem {
  id: string
  label: string
  route: string
  icon: string
  required_permission: string
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
  menu: DashboardMenuItem[]
  widgets: DashboardWidget[]
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
  resource: string
  action: string
  name: string
  description: string
  is_active: boolean
  created_at: string
  updated_at: string
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

