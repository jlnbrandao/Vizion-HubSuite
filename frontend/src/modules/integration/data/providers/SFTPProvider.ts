import type { Integration } from '../models/Integration'
import type {
  IntegrationSyncResult,
  IntegrationTestResult,
  SFTPConfig,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

export class SFTPProvider extends BaseIntegrationProvider {
  readonly type = 'sftp' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as SFTPConfig
    await delay(170)
    if (!config.host.trim() || !config.username.trim() || !config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Host, usuário ou credenciais SFTP ausentes.',
      }
    }
    return {
      success: true,
      message: 'Conexão SFTP realizada com sucesso',
      server: `${config.host}:${config.port}`,
      durationMs: 210,
      authentication: config.authType === 'password' ? 'SFTP password' : 'SFTP private key',
      permission: `${config.remotePath}; schedule=${config.scheduleCron || 'manual'}`,
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const config = integration.configuration as SFTPConfig
    const startedAt = new Date().toISOString()
    await delay(220)
    return {
      success: true,
      mode: 'full',
      recordsProcessed: 0,
      message: `SFTP pull (client stub) — use backend Sync. Pattern ${config.filenamePattern}, encoding ${config.encoding}.`,
      startedAt,
      finishedAt: new Date().toISOString(),
    }
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}
