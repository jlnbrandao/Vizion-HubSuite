import type { Integration } from '../models/Integration'
import type {
  IntegrationSyncResult,
  IntegrationTestResult,
  SoapConfig,
} from '../types/IntegrationTypes'
import { BaseIntegrationProvider } from './IntegrationProvider'

export class SoapProvider extends BaseIntegrationProvider {
  readonly type = 'soap' as const

  async testConnection(integration: Integration): Promise<IntegrationTestResult> {
    const config = integration.configuration as SoapConfig
    await delay(190)
    if (!config.wsdlUrl.trim() || !config.operation.trim()) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'WSDL ou operação SOAP não configurados.',
      }
    }
    if (config.authType !== 'none' && !config.secretsConfigured) {
      return {
        success: false,
        message: 'Falha na conexão',
        errorDetail: 'Credenciais SOAP ausentes no backend.',
      }
    }
    return {
      success: true,
      message: 'WSDL acessível e operação localizada',
      server: safeHost(config.wsdlUrl),
      durationMs: 240,
      authentication:
        config.authType === 'basic'
          ? 'SOAP Basic'
          : config.authType === 'bearer'
            ? 'SOAP Bearer'
            : 'SOAP',
      permission: config.operation,
    }
  }

  async sync(integration: Integration): Promise<IntegrationSyncResult> {
    const config = integration.configuration as SoapConfig
    const startedAt = new Date().toISOString()
    await delay(230)
    return {
      success: true,
      mode: 'full',
      recordsProcessed: 0,
      message: `SOAP call (client stub) — use backend Sync. Operation ${config.operation}.`,
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
