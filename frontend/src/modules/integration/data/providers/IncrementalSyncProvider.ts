import type { Integration } from '../models/Integration'
import type {
  IncrementalSyncConfig,
  IntegrationSyncResult,
  IntegrationTestResult,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

export class IncrementalSyncProvider extends BaseIntegrationProvider {
  readonly type = 'incremental_sync' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as IncrementalSyncConfig
    await delay(140)
    if (!config.baseUrl.trim()) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'URL base não configurada.',
      }
    }
    if (config.authType !== 'none' && !config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Credenciais ausentes no backend.',
      }
    }
    return {
      success: true,
      message: 'Endpoint incremental acessível',
      server: safeHost(config.baseUrl),
      durationMs: 134,
      authentication: config.authType,
      permission: `${config.cursorField} · page ${config.pageSize}`,
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const config = integration.configuration as IncrementalSyncConfig
    const startedAt = new Date().toISOString()
    await delay(200)
    return {
      success: true,
      mode: 'incremental',
      recordsProcessed: 0,
      message: `Incremental sync (client stub) — use backend Sync. Cursor field ${config.cursorField}.`,
      startedAt,
      finishedAt: new Date().toISOString(),
      cursorValue: config.cursorValue || null,
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
