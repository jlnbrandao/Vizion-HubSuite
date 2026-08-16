import type { AuthAdapter, AuthPrincipal, LoginResult } from './AuthAdapter'

interface HttpClient {
  post<T>(path: string, body?: unknown): Promise<T>
  get<T>(path: string, token?: string): Promise<T>
}

export class LocalAuthAdapter implements AuthAdapter {
  constructor(private readonly http: HttpClient) {}

  async login(login: string, password: string): Promise<LoginResult> {
    const data = await this.http.post<{
      access_token: string
      user_id: string
      email: string
      full_name: string
    }>('/auth/login', { login, password })
    const user = await this.me(data.access_token)
    return { accessToken: data.access_token, user }
  }

  async me(accessToken: string): Promise<AuthPrincipal> {
    const data = await this.http.get<{
      id: string
      email: string
      full_name: string
      tenant_id: string
      tenant_slug: string
      permissions: string[]
      services: string[]
    }>('/auth/me', accessToken)
    return {
      id: data.id,
      email: data.email,
      fullName: data.full_name,
      tenantId: data.tenant_id,
      tenantSlug: data.tenant_slug,
      permissions: data.permissions,
      services: data.services ?? [],
    }
  }

  async logout(accessToken: string): Promise<void> {
    await this.http.post('/auth/logout', { accessToken })
  }
}
