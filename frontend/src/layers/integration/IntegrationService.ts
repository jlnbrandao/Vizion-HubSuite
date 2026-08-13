import { api, apiErrorMessage } from '@/services/api'
import type { Integration } from './models/Integration'
import type {
  CreateIntegrationInput,
  IntegrationConfiguration,
  IntegrationLogEntry,
  IntegrationMethodType,
  IntegrationStatus,
  IntegrationSyncResult,
  IntegrationTestResult,
  UpdateIntegrationInput,
} from './types/IntegrationTypes'

interface ApiIntegration {
  id: string
  tenant_id: string
  name: string
  description: string
  type: IntegrationMethodType
  status: IntegrationStatus
  configuration: Record<string, unknown>
  secrets_configured: boolean
  created_at: string
  updated_at: string
  last_sync_at: string | null
  last_error: string | null
}

interface ApiLog {
  id: string
  integration_id: string
  level: 'info' | 'warning' | 'error'
  message: string
  created_at: string
}

/**
 * Facade used by the UI. ETAPA 2 persists via FastAPI; outbound HTTP stays on the server.
 */
export class IntegrationService {
  async list(): Promise<Integration[]> {
    const { data } = await api.get<ApiIntegration[]>('/integrations')
    return data.map(mapIntegration)
  }

  async getById(id: string): Promise<Integration | null> {
    try {
      const { data } = await api.get<ApiIntegration>(`/integrations/${id}`)
      return mapIntegration(data)
    } catch (error) {
      if (isNotFound(error)) return null
      throw new Error(apiErrorMessage(error, 'Failed to load integration'))
    }
  }

  async create(input: CreateIntegrationInput): Promise<Integration> {
    const { data } = await api.post<ApiIntegration>('/integrations', {
      name: input.name.trim(),
      description: input.description.trim(),
      type: input.type,
      status: input.status,
      configuration: input.configuration,
      secrets: input.secrets && Object.keys(input.secrets).length ? input.secrets : undefined,
    })
    return mapIntegration(data)
  }

  async update(id: string, input: UpdateIntegrationInput): Promise<Integration> {
    const payload: Record<string, unknown> = {}
    if (input.name !== undefined) payload.name = input.name.trim()
    if (input.description !== undefined) payload.description = input.description.trim()
    if (input.status !== undefined) payload.status = input.status
    if (input.configuration !== undefined) payload.configuration = input.configuration
    if (input.secrets !== undefined) payload.secrets = input.secrets
    const { data } = await api.put<ApiIntegration>(`/integrations/${id}`, payload)
    return mapIntegration(data)
  }

  async remove(id: string): Promise<void> {
    await api.delete(`/integrations/${id}`)
  }

  async test(id: string): Promise<IntegrationTestResult> {
    const { data } = await api.post<{
      success: boolean
      message: string
      server?: string | null
      duration_ms?: number | null
      authentication?: string | null
      permission?: string | null
      error_detail?: string | null
    }>(`/integrations/${id}/test`)
    return {
      success: data.success,
      message: data.message,
      server: data.server ?? undefined,
      durationMs: data.duration_ms ?? undefined,
      authentication: data.authentication ?? undefined,
      permission: data.permission ?? undefined,
      errorDetail: data.error_detail ?? undefined,
    }
  }

  async sync(id: string): Promise<IntegrationSyncResult> {
    const { data } = await api.post<{
      success: boolean
      mode: 'full' | 'incremental'
      records_processed: number
      message: string
      started_at: string
      finished_at: string
      cursor_value?: string | null
    }>(`/integrations/${id}/sync`)
    return {
      success: data.success,
      mode: data.mode,
      recordsProcessed: data.records_processed,
      message: data.message,
      startedAt: data.started_at,
      finishedAt: data.finished_at,
      cursorValue: data.cursor_value ?? null,
    }
  }

  async getStatus(id: string): Promise<IntegrationStatus> {
    const { data } = await api.get<{ status: IntegrationStatus }>(`/integrations/${id}/status`)
    return data.status
  }

  async getLogs(id: string): Promise<IntegrationLogEntry[]> {
    const { data } = await api.get<ApiLog[]>(`/integrations/${id}/logs`)
    return data.map((entry) => ({
      id: entry.id,
      integrationId: entry.integration_id,
      level: entry.level,
      message: entry.message,
      createdAt: entry.created_at,
    }))
  }
}

export const integrationService = new IntegrationService()

function mapIntegration(row: ApiIntegration): Integration {
  return {
    id: row.id,
    tenantId: row.tenant_id,
    name: row.name,
    description: row.description,
    type: row.type,
    status: row.status,
    configuration: denormalizeConfiguration(row.type, row.configuration, row.secrets_configured),
    secretsConfigured: row.secrets_configured,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    lastSyncAt: row.last_sync_at,
    lastError: row.last_error,
  }
}

function denormalizeConfiguration(
  type: IntegrationMethodType,
  configuration: Record<string, unknown>,
  secretsConfigured: boolean,
): IntegrationConfiguration {
  const c = configuration
  switch (type) {
    case 'rest':
      return {
        baseUrl: str(c.base_url ?? c.baseUrl),
        endpoint: str(c.endpoint, '/'),
        httpMethod: (str(c.http_method ?? c.httpMethod, 'GET') as 'GET'),
        authType: (str(c.auth_type ?? c.authType, 'none') as 'none'),
        timeoutMs: num(c.timeout_ms ?? c.timeoutMs, 30_000),
        rateLimitPerMinute: c.rate_limit_per_minute != null || c.rateLimitPerMinute != null
          ? num(c.rate_limit_per_minute ?? c.rateLimitPerMinute, 60)
          : undefined,
        pagination: (str(c.pagination, 'none') as 'none'),
      }
    case 'oauth2':
      return {
        tokenUrl: str(c.token_url ?? c.tokenUrl),
        clientId: str(c.client_id ?? c.clientId),
        scope: str(c.scope),
        grantType: (str(c.grant_type ?? c.grantType, 'client_credentials') as 'client_credentials'),
        endpoint: str(c.endpoint),
        secretsConfigured,
      }
    case 'mtls':
      return {
        baseUrl: str(c.base_url ?? c.baseUrl),
        endpoint: str(c.endpoint, '/'),
        secretsConfigured,
      }
    case 'webhook':
      return {
        eventTypes: Array.isArray(c.event_types ?? c.eventTypes)
          ? ((c.event_types ?? c.eventTypes) as string[])
          : [],
        signatureHeader: str(c.signature_header ?? c.signatureHeader, 'X-Signature'),
        secretsConfigured,
      }
    case 'sftp':
      return {
        host: str(c.host),
        port: num(c.port, 22),
        username: str(c.username),
        authType: (str(c.auth_type ?? c.authType, 'private_key') as
          | 'private_key'
          | 'password'),
        remotePath: str(c.remote_path ?? c.remotePath, '/'),
        filenamePattern: str(c.filename_pattern ?? c.filenamePattern, '*.csv'),
        encoding: str(c.encoding, 'utf-8'),
        delimiter: str(c.delimiter, ','),
        scheduleCron: str(c.schedule_cron ?? c.scheduleCron, '0 */6 * * *'),
        secretsConfigured,
      }
    case 'http_file':
      return {
        url: str(c.url),
        format: (str(c.format, 'json') as 'json' | 'csv'),
        authType: (str(c.auth_type ?? c.authType, 'none') as
          | 'none'
          | 'api_key'
          | 'bearer'),
        encoding: str(c.encoding, 'utf-8'),
        delimiter: str(c.delimiter, ','),
        apiKeyHeader: str(c.api_key_header ?? c.apiKeyHeader, 'X-API-Key'),
        timeoutMs: num(c.timeout_ms ?? c.timeoutMs, 30_000),
        secretsConfigured,
      }
    case 'soap':
      return {
        wsdlUrl: str(c.wsdl_url ?? c.wsdlUrl),
        operation: str(c.operation),
        soapAction: str(c.soap_action ?? c.soapAction),
        endpoint: str(c.endpoint),
        namespace: str(c.namespace, 'urn:integration'),
        authType: (str(c.auth_type ?? c.authType, 'none') as
          | 'none'
          | 'basic'
          | 'bearer'),
        timeoutMs: num(c.timeout_ms ?? c.timeoutMs, 30_000),
        secretsConfigured,
      }
    case 'incremental_sync':
      return {
        baseUrl: str(c.base_url ?? c.baseUrl),
        endpoint: str(c.endpoint, '/'),
        cursorField: str(c.cursor_field ?? c.cursorField, 'updated_since'),
        cursorValue: str(c.cursor_value ?? c.cursorValue),
        pageSize: num(c.page_size ?? c.pageSize, 100),
        authType: (str(c.auth_type ?? c.authType, 'none') as
          | 'none'
          | 'api_key'
          | 'bearer'),
        apiKeyHeader: str(c.api_key_header ?? c.apiKeyHeader, 'X-API-Key'),
        timeoutMs: num(c.timeout_ms ?? c.timeoutMs, 30_000),
        secretsConfigured,
      }
    case 'database':
      return {
        host: str(c.host),
        port: num(c.port, 5432),
        database: str(c.database),
        username: str(c.username),
        schema: str(c.schema, 'public'),
        table: str(c.table),
        query: str(c.query),
        rowLimit: num(c.row_limit ?? c.rowLimit, 1000),
        timeoutMs: num(c.timeout_ms ?? c.timeoutMs, 15_000),
        readOnly: true,
        secretsConfigured,
      }
  }
}

function str(value: unknown, fallback = ''): string {
  return value == null ? fallback : String(value)
}

function num(value: unknown, fallback: number): number {
  const n = Number(value)
  return Number.isFinite(n) ? n : fallback
}

function isNotFound(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    (error as { response?: { status?: number } }).response?.status === 404
  )
}
