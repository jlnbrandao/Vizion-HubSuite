/** Integration method identifiers — stable keys for providers and UI. */
export type IntegrationMethodType =
  | 'rest'
  | 'oauth2'
  | 'mtls'
  | 'webhook'
  | 'sftp'
  | 'http_file'
  | 'soap'
  | 'incremental_sync'
  | 'database'

export type IntegrationStatus =
  | 'ACTIVE'
  | 'INACTIVE'
  | 'ERROR'
  | 'TESTING'
  | 'SYNCING'
  | 'NEVER_SYNCED'

export type RecommendationTier = 'recommended' | 'alternative' | 'not_recommended'

export type SyncMode = 'full' | 'incremental'

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface MethodComparisonRow {
  type: IntegrationMethodType
  label: string
  complexity: string
  thirdPartyImpact: string
  security: string
  tier: RecommendationTier
  description: string
}

export interface IntegrationTestResult {
  success: boolean
  message: string
  server?: string
  durationMs?: number
  authentication?: string
  permission?: string
  errorDetail?: string
}

export interface IntegrationSyncResult {
  success: boolean
  mode: SyncMode
  recordsProcessed: number
  message: string
  startedAt: string
  finishedAt: string
  cursorValue?: string | null
}

export interface IntegrationLogEntry {
  id: string
  integrationId: string
  level: 'info' | 'warning' | 'error'
  message: string
  createdAt: string
}

/** Non-sensitive REST settings only — secrets stay on the backend. */
export interface RestConfig {
  baseUrl: string
  endpoint: string
  httpMethod: HttpMethod
  authType: 'none' | 'api_key' | 'bearer'
  timeoutMs: number
  rateLimitPerMinute?: number
  pagination: 'none' | 'offset' | 'cursor' | 'page'
}

export interface OAuth2Config {
  tokenUrl: string
  clientId: string
  scope: string
  grantType: 'client_credentials' | 'authorization_code'
  endpoint: string
  /** True when a secret ref exists server-side; never store the secret here. */
  secretsConfigured: boolean
}

export interface MTLSConfig {
  baseUrl: string
  endpoint: string
  secretsConfigured: boolean
}

export interface WebhookConfig {
  eventTypes: string[]
  signatureHeader: string
  secretsConfigured: boolean
}

export interface SFTPConfig {
  host: string
  port: number
  username: string
  authType: 'password' | 'private_key'
  remotePath: string
  filenamePattern: string
  encoding: string
  delimiter: string
  scheduleCron: string
  secretsConfigured: boolean
}

export interface HttpFileConfig {
  url: string
  format: 'json' | 'csv'
  authType: 'none' | 'api_key' | 'bearer'
  encoding: string
  delimiter?: string
  apiKeyHeader?: string
  timeoutMs?: number
  secretsConfigured: boolean
}

export interface SoapConfig {
  wsdlUrl: string
  operation: string
  soapAction?: string
  endpoint?: string
  namespace?: string
  authType: 'none' | 'basic' | 'bearer'
  timeoutMs?: number
  secretsConfigured: boolean
}

export interface IncrementalSyncConfig {
  baseUrl: string
  endpoint: string
  cursorField: string
  cursorValue?: string
  pageSize: number
  authType: 'none' | 'api_key' | 'bearer'
  apiKeyHeader?: string
  timeoutMs?: number
  secretsConfigured: boolean
}

export interface DatabaseConfig {
  host: string
  port: number
  database: string
  username: string
  schema?: string
  table?: string
  query?: string
  rowLimit?: number
  timeoutMs?: number
  readOnly: true
  secretsConfigured: boolean
}

export type IntegrationConfiguration =
  | RestConfig
  | OAuth2Config
  | MTLSConfig
  | WebhookConfig
  | SFTPConfig
  | HttpFileConfig
  | SoapConfig
  | IncrementalSyncConfig
  | DatabaseConfig

export interface CreateIntegrationInput {
  name: string
  description: string
  type: IntegrationMethodType
  status: IntegrationStatus
  configuration: IntegrationConfiguration
  /** Write-only — never returned by the API / never stored in browser persistence. */
  secrets?: Record<string, string>
}

export interface UpdateIntegrationInput {
  name?: string
  description?: string
  status?: IntegrationStatus
  configuration?: IntegrationConfiguration
  secrets?: Record<string, string>
}

export const METHOD_COMPARISON: MethodComparisonRow[] = [
  {
    type: 'rest',
    label: 'API REST',
    complexity: 'Baixa',
    thirdPartyImpact: 'Baixo',
    security: 'Alta',
    tier: 'recommended',
    description: 'HTTP REST com autenticação simples ou API key.',
  },
  {
    type: 'oauth2',
    label: 'API REST + OAuth 2.0',
    complexity: 'Média',
    thirdPartyImpact: 'Baixo',
    security: 'Muito alta',
    tier: 'recommended',
    description: 'REST com Client Credentials (preferencial).',
  },
  {
    type: 'mtls',
    label: 'API + mTLS',
    complexity: 'Média/Alta',
    thirdPartyImpact: 'Muito baixo',
    security: 'Muito alta',
    tier: 'recommended',
    description: 'Autenticação mútua por certificado.',
  },
  {
    type: 'webhook',
    label: 'Webhook',
    complexity: 'Média',
    thirdPartyImpact: 'Muito baixo',
    security: 'Muito alta',
    tier: 'recommended',
    description: 'Eventos push do terceiro para a plataforma.',
  },
  {
    type: 'sftp',
    label: 'SFTP / CSV',
    complexity: 'Baixa',
    thirdPartyImpact: 'Muito baixo',
    security: 'Alta',
    tier: 'alternative',
    description: 'Arquivos CSV via SFTP agendado.',
  },
  {
    type: 'http_file',
    label: 'HTTPS / JSON / CSV',
    complexity: 'Baixa',
    thirdPartyImpact: 'Muito baixo',
    security: 'Alta',
    tier: 'alternative',
    description: 'Download de arquivos JSON/CSV por HTTPS.',
  },
  {
    type: 'soap',
    label: 'SOAP',
    complexity: 'Média',
    thirdPartyImpact: 'Baixo',
    security: 'Alta',
    tier: 'alternative',
    description: 'Serviços SOAP legados (WSDL).',
  },
  {
    type: 'incremental_sync',
    label: 'Sincronização incremental',
    complexity: 'Média',
    thirdPartyImpact: 'Muito baixo',
    security: 'Alta',
    tier: 'recommended',
    description: 'Sync por cursor / updated_since.',
  },
  {
    type: 'database',
    label: 'Replicação / acesso DB',
    complexity: 'Alta',
    thirdPartyImpact: 'Médio/Alto',
    security: 'Média',
    tier: 'not_recommended',
    description: 'Acesso direto ao banco (somente leitura).',
  },
]

export const DATABASE_WARNING =
  'Acesso direto ao banco de dados do terceiro aumenta o acoplamento e pode gerar impacto operacional. Prefira API, Webhook, SFTP ou sincronização incremental sempre que possível.'

export function methodLabel(type: IntegrationMethodType): string {
  return METHOD_COMPARISON.find((row) => row.type === type)?.label ?? type
}

export function methodTier(type: IntegrationMethodType): RecommendationTier {
  return METHOD_COMPARISON.find((row) => row.type === type)?.tier ?? 'alternative'
}
