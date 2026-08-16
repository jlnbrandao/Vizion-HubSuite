import type { RuntimeConfig } from '../RuntimeConfig'
import type { AuthAdapter } from './AuthAdapter'
import { HubAuthAdapter } from './HubAuthAdapter'
import { LocalAuthAdapter } from './LocalAuthAdapter'

interface HttpClient {
  post<T>(path: string, body?: unknown): Promise<T>
  get<T>(path: string, token?: string): Promise<T>
}

export function createAuthAdapter(config: RuntimeConfig, http: HttpClient): AuthAdapter {
  if (config.mode === 'hub') {
    return new HubAuthAdapter(http)
  }
  return new LocalAuthAdapter(http)
}
