import type { Integration } from './models/Integration'
import type { IntegrationProvider } from './providers/IntegrationProvider'
import { DatabaseProvider } from './providers/DatabaseProvider'
import { HttpFileProvider } from './providers/HttpFileProvider'
import { IncrementalSyncProvider } from './providers/IncrementalSyncProvider'
import { MTLSProvider } from './providers/MTLSProvider'
import { OAuth2Provider } from './providers/OAuth2Provider'
import { RestProvider } from './providers/RestProvider'
import { SFTPProvider } from './providers/SFTPProvider'
import { SoapProvider } from './providers/SoapProvider'
import { WebhookProvider } from './providers/WebhookProvider'
import type {
  IntegrationMethodType,
  IntegrationSyncResult,
  IntegrationTestResult,
} from './types/IntegrationTypes'

/**
 * Selects the Strategy/Provider for a given integration method.
 * Page code must not import providers directly.
 */
export class IntegrationLayer {
  private readonly providers: Map<IntegrationMethodType, IntegrationProvider>

  constructor(providers?: IntegrationProvider[]) {
    const list =
      providers ??
      [
        new RestProvider(),
        new OAuth2Provider(),
        new MTLSProvider(),
        new WebhookProvider(),
        new SFTPProvider(),
        new HttpFileProvider(),
        new SoapProvider(),
        new IncrementalSyncProvider(),
        new DatabaseProvider(),
      ]
    this.providers = new Map(
      list.map((provider) => [provider.type as IntegrationMethodType, provider]),
    )
  }

  getProvider(type: IntegrationMethodType): IntegrationProvider {
    const provider = this.providers.get(type)
    if (!provider) {
      throw new Error(`No integration provider registered for type: ${type}`)
    }
    return provider
  }

  listRegisteredTypes(): IntegrationMethodType[] {
    return [...this.providers.keys()]
  }

  testConnection(integration: Integration): Promise<IntegrationTestResult> {
    return this.getProvider(integration.type).testConnection(integration)
  }

  fetch(integration: Integration): Promise<unknown> {
    return this.getProvider(integration.type).fetch(integration)
  }

  sync(integration: Integration): Promise<IntegrationSyncResult> {
    return this.getProvider(integration.type).sync(integration)
  }
}

export const integrationLayer = new IntegrationLayer()
