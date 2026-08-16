export interface AuthPrincipal {
  id: string
  email: string
  fullName: string
  tenantId: string
  tenantSlug: string
  permissions: string[]
  services: string[]
}

export interface LoginResult {
  accessToken: string
  user: AuthPrincipal
}

export interface AuthAdapter {
  login(login: string, password: string): Promise<LoginResult>
  me(accessToken: string): Promise<AuthPrincipal>
  logout(accessToken: string): Promise<void>
}
