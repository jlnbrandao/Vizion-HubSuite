import type { Integration } from '../models/Integration'
import type {
  IntegrationSyncResult,
  IntegrationTestResult,
  OAuth2Config,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

/** ETAPA 1 stub — tokens never surface to the UI. */
export class OAuth2Provider extends BaseIntegrationProvider {
  readonly type = 'oauth2' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as OAuth2Config
    await delay(150)
    if (!config.tokenUrl.trim() || !config.clientId.trim()) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Não foi possível autenticar no servidor terceiro.',
      }
    }
    if (!config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Client secret não configurado no backend.',
      }
    }
    return {
      success: true,
      message: 'Conexão realizada com sucesso',
      server: safeHost(config.tokenUrl),
      durationMs: 168,
      authentication: 'OAuth 2.0',
      permission: config.scope || 'addresses:read',
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const startedAt = new Date().toISOString()
    await delay(200)
    return {
      success: true,
      mode: 'full',
      recordsProcessed: 8,
      message: `Mock OAuth2 sync for ${integration.name}`,
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
