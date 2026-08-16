import type { AuthAdapter, AuthPrincipal, LoginResult } from './AuthAdapter'
import { LocalAuthAdapter } from './LocalAuthAdapter'

/**
 * Hub mode still talks to the product API. The product kernel federates
 * authentication to Platform Core server-side, so the SPA never branches on mode.
 */
export class HubAuthAdapter extends LocalAuthAdapter implements AuthAdapter {
  async login(login: string, password: string): Promise<LoginResult> {
    return super.login(login, password)
  }

  async me(accessToken: string): Promise<AuthPrincipal> {
    return super.me(accessToken)
  }
}
