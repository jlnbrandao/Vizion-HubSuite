import type { Integration } from '../models/Integration'
import type {
  IntegrationSyncResult,
  IntegrationTestResult,
} from '../types/IntegrationTypes'

/**
 * Strategy contract for each integration protocol.
 * Implementations must not run in the browser against third parties —
 * ETAPA 1 stubs return mock results; later stages call FastAPI.
 */
export interface IntegrationProvider {
  readonly type: string
  testConnection(integration: Integration): Promise<IntegrationTestResult>
  fetch(integration: Integration): Promise<unknown>
  sync(integration: Integration): Promise<IntegrationSyncResult>
}

export abstract class BaseIntegrationProvider implements IntegrationProvider {
  abstract readonly type: string

  abstract testConnection(integration: Integration): Promise<IntegrationTestResult>

  async fetch(_integration: Integration): Promise<unknown> {
    return { items: [], mock: true }
  }

  abstract sync(integration: Integration): Promise<IntegrationSyncResult>
}
