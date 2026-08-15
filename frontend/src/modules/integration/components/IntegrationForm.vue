<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import {
  DATABASE_WARNING,
  defaultConfigFor,
  methodLabel,
  type Integration,
  type IntegrationConfiguration,
  type IntegrationMethodType,
  type IntegrationStatus,
} from '@/modules/integration/data'

const props = defineProps<{
  modelValue: boolean
  methodType: IntegrationMethodType | null
  integration?: Integration | null
  saving?: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [
    payload: {
      name: string
      description: string
      type: IntegrationMethodType
      status: IntegrationStatus
      configuration: IntegrationConfiguration
      secrets?: Record<string, string>
    },
  ]
}>()

const form = reactive({
  name: '',
  description: '',
  status: 'NEVER_SYNCED' as IntegrationStatus,
  configuration: defaultConfigFor('rest') as IntegrationConfiguration,
  /** Ephemeral UI-only flag — never persisted as a secret value. */
  markSecretConfigured: false,
  /** Write-only secret inputs — cleared after submit; never read back from API. */
  bearerToken: '',
  apiKey: '',
  clientSecret: '',
  clientCertPem: '',
  clientKeyPem: '',
  caCertPem: '',
  webhookSecret: '',
  sftpPassword: '',
  sftpPrivateKeyPem: '',
  sftpPassphrase: '',
  soapUsername: '',
  soapPassword: '',
  dbPassword: '',
})

const isEdit = computed(() => Boolean(props.integration?.id))
const effectiveType = computed<IntegrationMethodType | null>(
  () => props.integration?.type ?? props.methodType,
)
const title = computed(() =>
  isEdit.value ? 'Editar integração' : 'Nova integração',
)

const statusOptions = [
  { label: 'Ativa', value: 'ACTIVE' },
  { label: 'Inativa', value: 'INACTIVE' },
  { label: 'Nunca sincronizada', value: 'NEVER_SYNCED' },
]

const httpMethods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const authTypes = [
  { label: 'Nenhuma', value: 'none' },
  { label: 'API Key (backend)', value: 'api_key' },
  { label: 'Bearer (backend)', value: 'bearer' },
]
const paginationOptions = [
  { label: 'Nenhuma', value: 'none' },
  { label: 'Offset', value: 'offset' },
  { label: 'Cursor', value: 'cursor' },
  { label: 'Page', value: 'page' },
]
const grantTypes = [
  { label: 'Client Credentials', value: 'client_credentials' },
  { label: 'Authorization Code', value: 'authorization_code' },
]
const fileFormats = [
  { label: 'JSON', value: 'json' },
  { label: 'CSV', value: 'csv' },
]
const sftpAuth = [
  { label: 'Private key (backend)', value: 'private_key' },
  { label: 'Password (backend)', value: 'password' },
]
const csvEncodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
const soapAuth = [
  { label: 'Nenhuma', value: 'none' },
  { label: 'Basic (backend)', value: 'basic' },
  { label: 'Bearer (backend)', value: 'bearer' },
]
const webhookEvents = [
  'address.created',
  'address.updated',
  'address.deleted',
]

watch(
  () => [props.modelValue, props.methodType, props.integration] as const,
  ([open]) => {
    if (!open) return
    if (props.integration) {
      form.name = props.integration.name
      form.description = props.integration.description
      form.status = props.integration.status
      form.configuration = structuredClone(props.integration.configuration)
      form.markSecretConfigured =
        props.integration.secretsConfigured || hasSecretsFlag(props.integration.configuration)
      form.bearerToken = ''
      form.apiKey = ''
      form.clientSecret = ''
      form.clientCertPem = ''
      form.clientKeyPem = ''
      form.caCertPem = ''
      form.webhookSecret = ''
      form.sftpPassword = ''
      form.sftpPrivateKeyPem = ''
      form.sftpPassphrase = ''
      form.soapUsername = ''
      form.soapPassword = ''
      form.dbPassword = ''
      return
    }
    const type = props.methodType ?? 'rest'
    form.name = ''
    form.description = ''
    form.status = 'NEVER_SYNCED'
    form.configuration = defaultConfigFor(type)
    form.markSecretConfigured = false
    form.bearerToken = ''
    form.apiKey = ''
    form.clientSecret = ''
    form.clientCertPem = ''
    form.clientKeyPem = ''
    form.caCertPem = ''
    form.webhookSecret = ''
    form.sftpPassword = ''
    form.sftpPrivateKeyPem = ''
    form.sftpPassphrase = ''
    form.soapUsername = ''
    form.soapPassword = ''
    form.dbPassword = ''
  },
)

function hasSecretsFlag(config: IntegrationConfiguration): boolean {
  return 'secretsConfigured' in config ? Boolean(config.secretsConfigured) : false
}

function applySecretFlag(config: IntegrationConfiguration): IntegrationConfiguration {
  if (!('secretsConfigured' in config)) {
    return config
  }
  return {
    ...config,
    secretsConfigured: form.markSecretConfigured || Boolean(config.secretsConfigured),
  }
}

function collectSecrets(type: IntegrationMethodType): Record<string, string> | undefined {
  const secrets: Record<string, string> = {}
  if (
    (type === 'rest' || type === 'http_file' || type === 'incremental_sync') &&
    'authType' in form.configuration
  ) {
    if (form.configuration.authType === 'bearer' && form.bearerToken.trim()) {
      secrets.bearer_token = form.bearerToken.trim()
    }
    if (form.configuration.authType === 'api_key' && form.apiKey.trim()) {
      secrets.api_key = form.apiKey.trim()
    }
  }
  if (type === 'oauth2' && form.clientSecret.trim()) {
    secrets.client_secret = form.clientSecret.trim()
  }
  if (type === 'mtls') {
    if (form.clientCertPem.trim()) secrets.client_cert_pem = form.clientCertPem.trim()
    if (form.clientKeyPem.trim()) secrets.client_key_pem = form.clientKeyPem.trim()
    if (form.caCertPem.trim()) secrets.ca_cert_pem = form.caCertPem.trim()
  }
  if (type === 'webhook' && form.webhookSecret.trim()) {
    secrets.webhook_secret = form.webhookSecret.trim()
  }
  if (type === 'sftp' && 'authType' in form.configuration) {
    if (form.configuration.authType === 'password' && form.sftpPassword.trim()) {
      secrets.password = form.sftpPassword.trim()
    }
    if (form.configuration.authType === 'private_key') {
      if (form.sftpPrivateKeyPem.trim()) {
        secrets.private_key_pem = form.sftpPrivateKeyPem.trim()
      }
      if (form.sftpPassphrase.trim()) {
        secrets.passphrase = form.sftpPassphrase.trim()
      }
    }
  }
  if (type === 'soap' && 'authType' in form.configuration) {
    if (form.configuration.authType === 'basic') {
      if (form.soapUsername.trim()) secrets.username = form.soapUsername.trim()
      if (form.soapPassword.trim()) secrets.password = form.soapPassword.trim()
    }
    if (form.configuration.authType === 'bearer' && form.bearerToken.trim()) {
      secrets.bearer_token = form.bearerToken.trim()
    }
  }
  if (type === 'database' && form.dbPassword.trim()) {
    secrets.password = form.dbPassword.trim()
  }
  return Object.keys(secrets).length ? secrets : undefined
}

const inboundWebhookUrl = computed(() => {
  if (!props.integration?.id) return ''
  return `/api/v1/integrations/${props.integration.id}/webhook/events`
})

function close() {
  emit('update:modelValue', false)
}

function onSubmit() {
  const type = effectiveType.value
  if (!type) return
  emit('submit', {
    name: form.name,
    description: form.description,
    type,
    status: form.status,
    configuration: applySecretFlag(structuredClone(form.configuration)),
    secrets: collectSecrets(type),
  })
}

const cfg = computed(() => form.configuration)
</script>

<template>
  <q-dialog
    :model-value="modelValue"
    persistent
    transition-show="fade"
    transition-hide="fade"
    class="integration-hub-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <q-card flat class="integration-hub-modal">
      <header class="integration-hub-modal__titlebar">
        <div>
          <h2 class="integration-hub-modal__title">{{ title }}</h2>
          <p v-if="effectiveType" class="integration-hub-modal__lead">
            Método: {{ methodLabel(effectiveType) }}
          </p>
        </div>
        <button
          type="button"
          class="integration-hub-modal__close-x"
          aria-label="Fechar"
          @click="close"
        >
          <q-icon name="close" size="18px" />
        </button>
      </header>

      <div class="integration-hub-modal__body">
        <q-banner
          v-if="effectiveType === 'database'"
          dense
          rounded
          class="bg-warning text-dark q-mb-md"
        >
          {{ DATABASE_WARNING }}
        </q-banner>

        <q-form
          id="integration-form"
          class="q-gutter-md"
          @submit.prevent="onSubmit"
        >
          <q-input
            v-model="form.name"
            label="Nome"
            outlined
            dense
            :rules="[(v) => !!String(v).trim() || 'Informe o nome']"
          />
          <q-input
            v-model="form.description"
            label="Descrição"
            outlined
            dense
            type="textarea"
            autogrow
          />
          <q-input
            label="Tenant"
            outlined
            dense
            readonly
            hint="Determinado pelo contexto autenticado no backend"
            :model-value="integration?.tenantId || '(contexto autenticado)'"
          />
          <q-select
            v-model="form.status"
            :options="statusOptions"
            label="Status"
            outlined
            dense
            emit-value
            map-options
          />

          <!-- REST -->
          <template v-if="effectiveType === 'rest' && 'baseUrl' in cfg">
            <q-separator />
            <div class="text-subtitle2">Configuração REST</div>
            <q-input v-model="(cfg as any).baseUrl" label="URL Base" outlined dense />
            <q-input v-model="(cfg as any).endpoint" label="Endpoint" outlined dense />
            <q-select
              v-model="(cfg as any).httpMethod"
              :options="httpMethods"
              label="Método HTTP"
              outlined
              dense
            />
            <q-select
              v-model="(cfg as any).authType"
              :options="authTypes"
              label="Autenticação"
              outlined
              dense
              emit-value
              map-options
            />
            <q-input
              v-if="(cfg as any).authType === 'bearer'"
              v-model="form.bearerToken"
              type="password"
              label="Bearer token"
              outlined
              dense
              autocomplete="new-password"
              :hint="
                form.markSecretConfigured || integration?.secretsConfigured
                  ? 'Deixe em branco para manter o token já salvo no backend'
                  : 'Enviado ao backend e armazenado cifrado — não fica no browser'
              "
            />
            <q-input
              v-if="(cfg as any).authType === 'api_key'"
              v-model="form.apiKey"
              type="password"
              label="API Key"
              outlined
              dense
              autocomplete="new-password"
              :hint="
                form.markSecretConfigured || integration?.secretsConfigured
                  ? 'Deixe em branco para manter a key já salva no backend'
                  : 'Enviada ao backend e armazenada cifrada — não fica no browser'
              "
            />
            <q-input
              v-model.number="(cfg as any).timeoutMs"
              type="number"
              label="Timeout (ms)"
              outlined
              dense
            />
            <q-input
              v-model.number="(cfg as any).rateLimitPerMinute"
              type="number"
              label="Rate limit (req/min)"
              outlined
              dense
            />
            <q-select
              v-model="(cfg as any).pagination"
              :options="paginationOptions"
              label="Paginação"
              outlined
              dense
              emit-value
              map-options
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              API keys e tokens são cifrados no backend (Fernet) — nunca em localStorage.
            </q-banner>
          </template>

          <!-- OAuth2 -->
          <template v-else-if="effectiveType === 'oauth2' && 'tokenUrl' in cfg">
            <q-separator />
            <div class="text-subtitle2">Configuração OAuth 2.0</div>
            <q-input v-model="(cfg as any).tokenUrl" label="Token URL" outlined dense />
            <q-input v-model="(cfg as any).clientId" label="Client ID" outlined dense />
            <q-input
              v-model="form.clientSecret"
              type="password"
              label="Client Secret"
              outlined
              dense
              autocomplete="new-password"
              :hint="
                form.markSecretConfigured || integration?.secretsConfigured
                  ? 'Deixe em branco para manter o secret já salvo no backend'
                  : 'Enviado ao backend e cifrado — access tokens nunca voltam ao browser'
              "
            />
            <q-input
              v-model="(cfg as any).scope"
              label="Scope"
              outlined
              dense
              hint="Ex.: addresses:read"
            />
            <q-select
              v-model="(cfg as any).grantType"
              :options="grantTypes"
              label="Grant Type"
              outlined
              dense
              emit-value
              map-options
            />
            <q-input
              v-model="(cfg as any).endpoint"
              label="Endpoint do recurso"
              outlined
              dense
              hint="URL completa do recurso (ex.: https://api.partner.example/v1/addresses)"
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              Client Credentials no backend: o access token é obtido e renovado no servidor e
              nunca é exposto na API nem no Vue.
            </q-banner>
          </template>

          <!-- mTLS -->
          <template v-else-if="effectiveType === 'mtls' && 'baseUrl' in cfg">
            <q-separator />
            <div class="text-subtitle2">Configuração mTLS</div>
            <q-input v-model="(cfg as any).baseUrl" label="URL Base" outlined dense />
            <q-input v-model="(cfg as any).endpoint" label="Endpoint" outlined dense />
            <q-input
              v-model="form.clientCertPem"
              type="textarea"
              autogrow
              outlined
              dense
              label="Client Certificate (PEM)"
              :hint="
                form.markSecretConfigured || integration?.secretsConfigured
                  ? 'Deixe em branco para manter o certificado já salvo no backend'
                  : 'PEM enviado ao backend e cifrado — nunca fica em localStorage'
              "
            />
            <q-input
              v-model="form.clientKeyPem"
              type="textarea"
              autogrow
              outlined
              dense
              label="Private Key (PEM)"
              autocomplete="new-password"
              :hint="
                form.markSecretConfigured || integration?.secretsConfigured
                  ? 'Deixe em branco para manter a chave já salva no backend'
                  : 'Chave privada só no backend (Fernet)'
              "
            />
            <q-input
              v-model="form.caCertPem"
              type="textarea"
              autogrow
              outlined
              dense
              label="CA Certificate (PEM, opcional)"
              hint="CA do servidor terceiro; se vazio, usa trust store do sistema"
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              mTLS: certificado, chave e CA permanecem no backend. A API nunca devolve material PEM.
            </q-banner>
          </template>

          <!-- Webhook -->
          <template v-else-if="effectiveType === 'webhook' && 'eventTypes' in cfg">
            <q-separator />
            <div class="text-subtitle2">Configuração Webhook</div>
            <q-input
              v-if="inboundWebhookUrl"
              :model-value="inboundWebhookUrl"
              label="URL inbound (terceiro → plataforma)"
              outlined
              dense
              readonly
              hint="POST no Host do tenant; autenticação via HMAC (sem JWT)"
            />
            <q-banner v-else dense class="bg-grey-2 text-grey-8">
              Após salvar, a URL inbound
              <code>/api/v1/integrations/{id}/webhook/events</code>
              fica disponível neste formulário.
            </q-banner>
            <q-select
              v-model="(cfg as any).eventTypes"
              :options="webhookEvents"
              label="Eventos"
              outlined
              dense
              multiple
              use-chips
            />
            <q-input
              v-model="(cfg as any).signatureHeader"
              label="Header de assinatura"
              outlined
              dense
              hint="Ex.: X-Signature (aceita também sha256=&lt;hex&gt;)"
            />
            <q-input
              v-model="form.webhookSecret"
              type="password"
              outlined
              dense
              label="Segredo HMAC (write-only)"
              :hint="
                form.markSecretConfigured || isEdit
                  ? 'Deixe em branco para manter o segredo já salvo no backend'
                  : 'Obrigatório para receber eventos assinados'
              "
              autocomplete="new-password"
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              Webhook: o segredo permanece no backend. A API nunca devolve o valor.
            </q-banner>
          </template>

          <!-- SFTP -->
          <template v-else-if="effectiveType === 'sftp' && 'host' in cfg">
            <q-separator />
            <div class="text-subtitle2">Configuração SFTP</div>
            <q-input v-model="(cfg as any).host" label="Host" outlined dense />
            <q-input v-model.number="(cfg as any).port" type="number" label="Port" outlined dense />
            <q-input v-model="(cfg as any).username" label="Username" outlined dense />
            <q-select
              v-model="(cfg as any).authType"
              :options="sftpAuth"
              label="Authentication"
              outlined
              dense
              emit-value
              map-options
            />
            <q-input
              v-if="(cfg as any).authType === 'password'"
              v-model="form.sftpPassword"
              type="password"
              outlined
              dense
              label="Password (write-only)"
              :hint="
                form.markSecretConfigured || isEdit
                  ? 'Deixe em branco para manter a senha já salva no backend'
                  : 'Obrigatória para autenticação por senha'
              "
              autocomplete="new-password"
            />
            <template v-else>
              <q-input
                v-model="form.sftpPrivateKeyPem"
                type="textarea"
                autogrow
                outlined
                dense
                label="Private key PEM (write-only)"
                :hint="
                  form.markSecretConfigured || isEdit
                    ? 'Deixe em branco para manter a chave já salva no backend'
                    : 'Chave RSA ou Ed25519 em PEM'
                "
              />
              <q-input
                v-model="form.sftpPassphrase"
                type="password"
                outlined
                dense
                label="Passphrase da chave (opcional, write-only)"
                autocomplete="new-password"
              />
            </template>
            <q-input v-model="(cfg as any).remotePath" label="Remote Path" outlined dense />
            <q-input
              v-model="(cfg as any).filenamePattern"
              label="Filename Pattern"
              outlined
              dense
              hint="Glob, ex.: *.csv ou addresses_*.csv"
            />
            <q-select
              v-model="(cfg as any).encoding"
              :options="csvEncodings"
              label="CSV encoding"
              outlined
              dense
              use-input
              new-value-mode="add"
            />
            <q-input
              v-model="(cfg as any).delimiter"
              label="CSV delimiter"
              outlined
              dense
              maxlength="1"
            />
            <q-input
              v-model="(cfg as any).scheduleCron"
              label="Schedule (cron)"
              outlined
              dense
              hint="Metadado para sync pull agendado; sync manual via ação Sync"
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              SFTP: senha/chave permanecem no backend. A API nunca devolve credenciais.
            </q-banner>
          </template>

          <!-- HTTP File -->
          <template v-else-if="effectiveType === 'http_file' && 'url' in cfg">
            <q-separator />
            <div class="text-subtitle2">Configuração HTTPS arquivo</div>
            <q-input
              v-model="(cfg as any).url"
              label="URL"
              outlined
              dense
              hint="Download server-side (http/https)"
            />
            <q-select
              v-model="(cfg as any).format"
              :options="fileFormats"
              label="Formato"
              outlined
              dense
              emit-value
              map-options
            />
            <q-select
              v-model="(cfg as any).authType"
              :options="authTypes"
              label="Autenticação"
              outlined
              dense
              emit-value
              map-options
            />
            <q-input
              v-if="(cfg as any).authType === 'bearer'"
              v-model="form.bearerToken"
              type="password"
              outlined
              dense
              label="Bearer token (write-only)"
              :hint="
                form.markSecretConfigured || isEdit
                  ? 'Deixe em branco para manter o token já salvo no backend'
                  : 'Obrigatório para autenticação Bearer'
              "
              autocomplete="new-password"
            />
            <template v-if="(cfg as any).authType === 'api_key'">
              <q-input
                v-model="form.apiKey"
                type="password"
                outlined
                dense
                label="API Key (write-only)"
                :hint="
                  form.markSecretConfigured || isEdit
                    ? 'Deixe em branco para manter a key já salva no backend'
                    : 'Obrigatória para autenticação API Key'
                "
                autocomplete="new-password"
              />
              <q-input
                v-model="(cfg as any).apiKeyHeader"
                label="Header da API Key"
                outlined
                dense
              />
            </template>
            <q-select
              v-model="(cfg as any).encoding"
              :options="csvEncodings"
              label="Encoding"
              outlined
              dense
              use-input
              new-value-mode="add"
            />
            <q-input
              v-if="(cfg as any).format === 'csv'"
              v-model="(cfg as any).delimiter"
              label="Delimitador CSV"
              outlined
              dense
              maxlength="1"
            />
            <q-input
              v-model.number="(cfg as any).timeoutMs"
              type="number"
              label="Timeout (ms)"
              outlined
              dense
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              HTTPS file: tokens/keys permanecem no backend. A API nunca devolve segredos.
            </q-banner>
          </template>

          <!-- SOAP -->
          <template v-else-if="effectiveType === 'soap' && 'wsdlUrl' in cfg">
            <q-separator />
            <div class="text-subtitle2">Configuração SOAP</div>
            <q-input
              v-model="(cfg as any).wsdlUrl"
              label="WSDL URL"
              outlined
              dense
              hint="GET no backend para validar WSDL + operação"
            />
            <q-input v-model="(cfg as any).operation" label="Operation" outlined dense />
            <q-input
              v-model="(cfg as any).soapAction"
              label="SOAPAction"
              outlined
              dense
              hint="Se vazio, usa o nome da operation"
            />
            <q-input
              v-model="(cfg as any).endpoint"
              label="Endpoint SOAP (opcional)"
              outlined
              dense
              hint="Se vazio, deriva da URL do WSDL (remove ?wsdl)"
            />
            <q-input
              v-model="(cfg as any).namespace"
              label="Namespace do body"
              outlined
              dense
            />
            <q-select
              v-model="(cfg as any).authType"
              :options="soapAuth"
              label="Autenticação"
              outlined
              dense
              emit-value
              map-options
            />
            <template v-if="(cfg as any).authType === 'basic'">
              <q-input
                v-model="form.soapUsername"
                outlined
                dense
                label="Username (write-only)"
                autocomplete="off"
              />
              <q-input
                v-model="form.soapPassword"
                type="password"
                outlined
                dense
                label="Password (write-only)"
                :hint="
                  form.markSecretConfigured || isEdit
                    ? 'Deixe em branco para manter a senha já salva no backend'
                    : 'Obrigatória para Basic auth'
                "
                autocomplete="new-password"
              />
            </template>
            <q-input
              v-if="(cfg as any).authType === 'bearer'"
              v-model="form.bearerToken"
              type="password"
              outlined
              dense
              label="Bearer token (write-only)"
              :hint="
                form.markSecretConfigured || isEdit
                  ? 'Deixe em branco para manter o token já salvo no backend'
                  : 'Obrigatório para Bearer'
              "
              autocomplete="new-password"
            />
            <q-input
              v-model.number="(cfg as any).timeoutMs"
              type="number"
              label="Timeout (ms)"
              outlined
              dense
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              SOAP: credenciais permanecem no backend. A API nunca devolve segredos.
            </q-banner>
          </template>

          <!-- Incremental -->
          <template v-else-if="effectiveType === 'incremental_sync' && 'cursorField' in cfg">
            <q-separator />
            <div class="text-subtitle2">Sincronização incremental</div>
            <q-input v-model="(cfg as any).baseUrl" label="URL Base" outlined dense />
            <q-input v-model="(cfg as any).endpoint" label="Endpoint" outlined dense />
            <q-input
              v-model="(cfg as any).cursorField"
              label="Campo cursor / updated_since"
              outlined
              dense
              hint="Query param enviado em cada página (ex.: updated_since)"
            />
            <q-input
              :model-value="(cfg as any).cursorValue || '—'"
              label="Cursor persistido"
              outlined
              dense
              readonly
              hint="Atualizado automaticamente após Sync bem-sucedido"
            />
            <q-input
              v-model.number="(cfg as any).pageSize"
              type="number"
              label="Page size"
              outlined
              dense
            />
            <q-select
              v-model="(cfg as any).authType"
              :options="authTypes"
              label="Autenticação"
              outlined
              dense
              emit-value
              map-options
            />
            <q-input
              v-if="(cfg as any).authType === 'bearer'"
              v-model="form.bearerToken"
              type="password"
              outlined
              dense
              label="Bearer token (write-only)"
              autocomplete="new-password"
            />
            <template v-if="(cfg as any).authType === 'api_key'">
              <q-input
                v-model="form.apiKey"
                type="password"
                outlined
                dense
                label="API Key (write-only)"
                autocomplete="new-password"
              />
              <q-input
                v-model="(cfg as any).apiKeyHeader"
                label="Header da API Key"
                outlined
                dense
              />
            </template>
            <q-input
              v-model.number="(cfg as any).timeoutMs"
              type="number"
              label="Timeout (ms)"
              outlined
              dense
            />
            <q-banner dense class="bg-grey-2 text-grey-8">
              Incremental: o cursor fica no backend após cada Sync. Segredos nunca voltam na API.
            </q-banner>
          </template>

          <!-- Database -->
          <template v-else-if="effectiveType === 'database' && 'database' in cfg">
            <q-separator />
            <div class="text-subtitle2">Banco de dados (somente leitura)</div>
            <q-banner dense rounded class="bg-warning text-dark">
              {{ DATABASE_WARNING }}
            </q-banner>
            <q-input v-model="(cfg as any).host" label="Host" outlined dense />
            <q-input v-model.number="(cfg as any).port" type="number" label="Port" outlined dense />
            <q-input v-model="(cfg as any).database" label="Database" outlined dense />
            <q-input v-model="(cfg as any).username" label="Username" outlined dense />
            <q-input
              v-model="form.dbPassword"
              type="password"
              outlined
              dense
              label="Password (write-only)"
              :hint="
                form.markSecretConfigured || isEdit
                  ? 'Deixe em branco para manter a senha já salva no backend'
                  : 'Obrigatória para conectar'
              "
              autocomplete="new-password"
            />
            <q-input v-model="(cfg as any).schema" label="Schema" outlined dense />
            <q-input
              v-model="(cfg as any).table"
              label="Tabela (sync)"
              outlined
              dense
              hint="Identificador simples; alternativa: query SELECT abaixo"
            />
            <q-input
              v-model="(cfg as any).query"
              type="textarea"
              autogrow
              outlined
              dense
              label="Query SELECT (opcional)"
              hint="Apenas SELECT/WITH — INSERT/UPDATE/DELETE são rejeitados"
            />
            <q-input
              v-model.number="(cfg as any).rowLimit"
              type="number"
              label="Limite de linhas"
              outlined
              dense
            />
            <q-input
              v-model.number="(cfg as any).timeoutMs"
              type="number"
              label="Timeout (ms)"
              outlined
              dense
            />
            <q-toggle :model-value="true" disable label="Read-only (obrigatório)" color="primary" />
            <q-banner dense class="bg-grey-2 text-grey-8">
              Database: senha permanece no backend; sessão sempre
              <code>default_transaction_read_only=on</code>.
            </q-banner>
          </template>

        </q-form>
      </div>

      <footer class="integration-hub-modal__footer">
        <span class="integration-hub-modal__footer-hint">
          Segredos ficam só no backend e nunca são devolvidos pela API.
        </span>
        <div class="integration-hub-modal__footer-actions">
          <q-btn outline color="grey-8" label="Cancelar" @click="close" />
          <q-btn
            form="integration-form"
            type="submit"
            unelevated
            color="primary"
            :label="isEdit ? 'Salvar' : 'Criar'"
            :loading="saving"
          />
        </div>
      </footer>
    </q-card>
  </q-dialog>
</template>
