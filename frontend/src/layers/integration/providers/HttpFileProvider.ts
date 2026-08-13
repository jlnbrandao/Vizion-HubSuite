import type { Integration } from '../models/Integration'
import type {
  HttpFileConfig,
  IntegrationSyncResult,
  IntegrationTestResult,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

export class HttpFileProvider extends BaseIntegrationProvider {
  readonly type = 'http_file' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as HttpFileConfig
    await delay(130)
    if (!config.url.trim()) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'URL do arquivo não configurada.',
      }
    }
    if (config.authType !== 'none' && !config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Credenciais de autenticação ausentes no backend.',
      }
    }
    return {
      success: true,
      message: 'Arquivo HTTPS acessível',
      server: safeHost(config.url),
      durationMs: 125,
      authentication: config.authType,
      permission: config.format.toUpperCase(),
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const config = integration.configuration as HttpFileConfig
    const startedAt = new Date().toISOString()
    await delay(180)
    return {
      success: true,
      mode: 'full',
      recordsProcessed: 0,
      message: `HTTPS file pull (client stub) — use backend Sync. Format ${config.format}, encoding ${config.encoding}.`,
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
