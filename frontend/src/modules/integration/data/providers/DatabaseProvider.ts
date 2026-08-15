import type { Integration } from '../models/Integration'
import type {
  DatabaseConfig,
  IntegrationSyncResult,
  IntegrationTestResult,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

/** Read-only stub — write operations must never be enabled. */
export class DatabaseProvider extends BaseIntegrationProvider {
  readonly type = 'database' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as DatabaseConfig
    await delay(180)
    if (!config.host.trim() || !config.database.trim() || !config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Host, database ou credenciais não configurados.',
      }
    }
    if (!config.readOnly) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Integração database exige readOnly=true.',
      }
    }
    return {
      success: true,
      message: 'Conexão realizada com sucesso (somente leitura)',
      server: `${config.host}:${config.port}/${config.database}`,
      durationMs: 175,
      authentication: 'DB credentials',
      permission: `SELECT only · schema=${config.schema || 'public'}`,
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const config = integration.configuration as DatabaseConfig
    const startedAt = new Date().toISOString()
    await delay(250)
    return {
      success: true,
      mode: 'full',
      recordsProcessed: 0,
      message: `DB read-only sync (client stub) — use backend Sync. Table ${config.table || '—'}.`,
      startedAt,
      finishedAt: new Date().toISOString(),
    }
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
