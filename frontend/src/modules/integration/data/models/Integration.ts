import type {
  IntegrationConfiguration,
  IntegrationMethodType,
  IntegrationStatus,
} from '../types/IntegrationTypes'

/**
 * Domain model for an Integration.
 * Sensitive credentials are never stored here — only opaque secret flags / backend refs.
 */
export interface Integration {
  id: string
  tenantId: string
  name: string
  description: string
  type: IntegrationMethodType
  status: IntegrationStatus
  configuration: IntegrationConfiguration
  /** True when encrypted secrets exist server-side (never includes secret values). */
  secretsConfigured: boolean
  createdAt: string
  updatedAt: string
  lastSyncAt: string | null
  lastError: string | null
}

export function createEmptyIntegration(
  partial: Partial<Integration> & Pick<Integration, 'type' | 'name'>,
): Integration {
  const now = new Date().toISOString()
  return {
    id: partial.id ?? '',
    tenantId: partial.tenantId ?? '',
    name: partial.name,
    description: partial.description ?? '',
    type: partial.type,
    status: partial.status ?? 'NEVER_SYNCED',
    configuration: partial.configuration ?? defaultConfigFor(partial.type),
    secretsConfigured: partial.secretsConfigured ?? false,
    createdAt: partial.createdAt ?? now,
    updatedAt: partial.updatedAt ?? now,
    lastSyncAt: partial.lastSyncAt ?? null,
    lastError: partial.lastError ?? null,
  }
}

export function defaultConfigFor(type: IntegrationMethodType): IntegrationConfiguration {
  switch (type) {
    case 'rest':
      return {
        baseUrl: '',
        endpoint: '/',
        httpMethod: 'GET',
        authType: 'none',
        timeoutMs: 30_000,
        pagination: 'none',
      }
    case 'oauth2':
      return {
        tokenUrl: '',
        clientId: '',
        scope: '',
        grantType: 'client_credentials',
        endpoint: '',
        secretsConfigured: false,
      }
    case 'mtls':
      return {
        baseUrl: '',
        endpoint: '/',
        secretsConfigured: false,
      }
    case 'webhook':
      return {
        eventTypes: ['address.created', 'address.updated', 'address.deleted'],
        signatureHeader: 'X-Signature',
        secretsConfigured: false,
      }
    case 'sftp':
      return {
        host: '',
        port: 22,
        username: '',
        authType: 'private_key',
        remotePath: '/',
        filenamePattern: '*.csv',
        encoding: 'utf-8',
        delimiter: ',',
        scheduleCron: '0 */6 * * *',
        secretsConfigured: false,
      }
    case 'http_file':
      return {
        url: '',
        format: 'json',
        authType: 'none',
        encoding: 'utf-8',
        delimiter: ',',
        apiKeyHeader: 'X-API-Key',
        timeoutMs: 30_000,
        secretsConfigured: false,
      }
    case 'soap':
      return {
        wsdlUrl: '',
        operation: '',
        soapAction: '',
        endpoint: '',
        namespace: 'urn:integration',
        authType: 'none',
        timeoutMs: 30_000,
        secretsConfigured: false,
      }
    case 'incremental_sync':
      return {
        baseUrl: '',
        endpoint: '/',
        cursorField: 'updated_since',
        cursorValue: '',
        pageSize: 100,
        authType: 'none',
        apiKeyHeader: 'X-API-Key',
        timeoutMs: 30_000,
        secretsConfigured: false,
      }
    case 'database':
      return {
        host: '',
        port: 5432,
        database: '',
        username: '',
        schema: 'public',
        table: '',
        query: '',
        rowLimit: 1000,
        timeoutMs: 15_000,
        readOnly: true,
        secretsConfigured: false,
      }
  }
}
