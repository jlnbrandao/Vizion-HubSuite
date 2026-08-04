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
  role_names: string[]
  permissions: string[]
  menu: DashboardMenuItem[]
  widgets: DashboardWidget[]
}

export interface AuthUser {
  id: string
  email: string
  fullName: string
  roleNames: string[]
  permissions: string[]
}
