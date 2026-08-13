import type { Integration } from '../models/Integration'
import type {
  IntegrationSyncResult,
  IntegrationTestResult,
  MTLSConfig,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

export class MTLSProvider extends BaseIntegrationProvider {
  readonly type = 'mtls' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as MTLSConfig
    await delay(160)
    if (!config.baseUrl.trim() || !config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Certificado cliente ou CA não configurados no backend.',
      }
    }
    return {
      success: true,
      message: 'Conexão realizada com sucesso',
      server: safeHost(config.baseUrl),
      durationMs: 155,
      authentication: 'mTLS',
      permission: 'mutual-tls',
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const startedAt = new Date().toISOString()
    await delay(190)
    return {
      success: true,
      mode: 'full',
      recordsProcessed: 5,
      message: `Mock mTLS sync for ${integration.name}`,
      startedAt,
      finishedAt: new Date().toISOString(),
    }
  }
}

function safeHost(url: string): string {
  try {
    return new URL(url).host || url
  } catch {
    return url || '—'
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
