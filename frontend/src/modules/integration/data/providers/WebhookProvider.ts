import type { Integration } from '../models/Integration'
import type {
  IntegrationSyncResult,
  IntegrationTestResult,
  WebhookConfig,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

export class WebhookProvider extends BaseIntegrationProvider {
  readonly type = 'webhook' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as WebhookConfig
    await delay(100)
    if (!config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Segredo de assinatura do webhook não configurado no backend.',
      }
    }
    return {
      success: true,
      message: 'Endpoint de webhook pronto para receber eventos',
      server: 'inbound-webhook (platform)',
      durationMs: 88,
      authentication: 'HMAC signature',
      permission: config.eventTypes.join(', ') || '—',
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const startedAt = new Date().toISOString()
    await delay(80)
    return {
      success: true,
      mode: 'incremental',
      recordsProcessed: 0,
      message: `Webhooks are push-based; no pull sync for ${integration.name}`,
      startedAt,
      finishedAt: new Date().toISOString(),
    }
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
