import type { Integration } from '../models/Integration'
import type {
  IntegrationSyncResult,
  IntegrationTestResult,
  RestConfig,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

/** ETAPA 1 stub — real REST calls arrive in ETAPA 2 via FastAPI. */
export class RestProvider extends BaseIntegrationProvider {
  readonly type = 'rest' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as RestConfig
    const host = safeHost(config.baseUrl)
    await delay(120)
    if (!config.baseUrl.trim()) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'URL base não configurada.',
      }
    }
    return {
      success: true,
      message: 'Conexão realizada com sucesso',
      server: host,
      durationMs: 142,
      authentication: config.authType === 'none' ? 'Nenhuma' : config.authType,
      permission: 'addresses:read',
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const startedAt = new Date().toISOString()
    await delay(180)
    return {
      success: true,
      mode: 'full',
      recordsProcessed: 12,
      message: `Mock sync for ${integration.name}`,
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
