<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar, type QTableColumn } from 'quasar'
import { usePermissions } from '@/composables/usePermissions'
import { PermissionCode } from '@/constants/permissions'
import { apiErrorMessage, billingApi } from '@/services/api'
import type {
  BillingChargeLine,
  BillingInvoiceResponse,
  BillingOverviewResponse,
  BillingPaymentMethodResponse,
  BillingSettingsResponse,
} from '@/types/api'
import visaIcon from '@/assets/payment-methods/visa.svg'
import mastercardIcon from '@/assets/payment-methods/mastercard.svg'
import amexIcon from '@/assets/payment-methods/amex.svg'
import pixIcon from '@/assets/payment-methods/pix.svg'
import boletoIcon from '@/assets/payment-methods/boleto.svg'
import cardIcon from '@/assets/payment-methods/card.svg'

const $q = useQuasar()
const router = useRouter()
const { can } = usePermissions()

const activeTab = ref<'overview' | 'history' | 'settings'>('overview')
const loading = ref(false)
const lastUpdate = ref<Date | null>(null)
const overview = ref<BillingOverviewResponse | null>(null)
const invoices = ref<BillingInvoiceResponse[]>([])
const paymentMethods = ref<BillingPaymentMethodResponse[]>([])
const settings = ref<BillingSettingsResponse | null>(null)
const paymentMethodsError = ref<string | null>(null)
const settingsError = ref<string | null>(null)
const loadingPaymentMethods = ref(false)
const loadingSettings = ref(false)

const usersExpanded = ref(false)
const servicesExpanded = ref(false)
const promoCode = ref('')
const showPaymentModal = ref(false)
const showAddCardModal = ref(false)
const showAddressModal = ref(false)
const paymentAmount = ref<'estimated' | 'custom'>('estimated')
const customAmount = ref(0)
const customAmountDisplay = ref('')
const selectedPaymentType = ref('PIX')
const selectedMethodId = ref<string | null>(null)
const paying = ref(false)
const savingCard = ref(false)
const savingSettings = ref(false)
const newCard = ref({
  holder_name: '',
  card_number: '',
  expiry: '',
  ccv: '',
})

const usersPagination = ref({ page: 1, rowsPerPage: 5 })
const servicesPagination = ref({ page: 1, rowsPerPage: 5 })

const canPay = computed(() => can(PermissionCode.PAYMENTS_CREATE))
const canManageMethods = computed(() => can(PermissionCode.PAYMENT_METHODS_MANAGE))
const canUpdateSettings = computed(() => can(PermissionCode.BILLING_SETTINGS_UPDATE))
const canExport = computed(() => can(PermissionCode.INVOICES_EXPORT))
const canViewUsers = computed(() => can(PermissionCode.USERS_READ))

const users = computed(() => overview.value?.users ?? [])
const services = computed(() => overview.value?.services ?? [])
const usersTotal = computed(() => users.value.reduce((sum, row) => sum + money(row.amount), 0))
const servicesTotal = computed(() =>
  services.value.reduce((sum, row) => sum + money(row.amount), 0),
)
const allExpanded = computed(() => usersExpanded.value && servicesExpanded.value)
const hasAddress = computed(() => Boolean(settings.value?.address))
const contractedServices = computed(
  () => settings.value?.contracted_services ?? services.value,
)

const usersColumns: QTableColumn[] = [
  { name: 'user', label: 'Usuário', field: 'label', align: 'left' },
  { name: 'detail', label: 'Detalhe', field: 'quantity', align: 'left' },
  { name: 'cost', label: 'Valor', field: 'amount', align: 'right' },
]

const servicesColumns: QTableColumn[] = [
  { name: 'service', label: 'Serviço', field: 'label', align: 'left' },
  { name: 'cost', label: 'Valor', field: 'amount', align: 'right' },
]

const historyColumns: QTableColumn[] = [
  { name: 'date', label: 'Data', field: 'created_at', align: 'left' },
  { name: 'description', label: 'Descrição', field: 'description', align: 'left' },
  { name: 'amount', label: 'Valor', field: 'total', align: 'right' },
  { name: 'status', label: 'Status', field: 'status', align: 'left' },
  { name: 'invoice', label: 'Fatura', field: 'id', align: 'right' },
]

const cycleOptions = [
  { label: 'Dia 3', value: 3 },
  { label: 'Dia 6', value: 6 },
  { label: 'Dia 9', value: 9 },
]

const paymentMethodOptions = computed(() =>
  paymentMethods.value.map((method) => ({
    label: methodLabel(method),
    value: method.id,
    method,
  })),
)

function money(value: string | number | undefined | null): number {
  return Number(value ?? 0)
}

function formatCurrency(value: string | number | undefined | null): string {
  return money(value).toFixed(2).replace('.', ',')
}

function formatDiscount(value: string | number | undefined | null): string {
  const amount = Math.abs(money(value))
  if (amount === 0) return '0,00'
  return `-${amount.toFixed(2).replace('.', ',')}`
}

function formatDate(value: string | undefined | null): string {
  if (!value) return '—'
  return new Date(value).toLocaleDateString('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })
}

function formatLastUpdate(): string {
  if (!lastUpdate.value || Number.isNaN(lastUpdate.value.getTime())) {
    return 'Última atualização: —'
  }
  const dateStr = lastUpdate.value
    .toLocaleString('pt-BR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
    .replace(',', '')
  return `Última atualização: ${dateStr}`
}

function monthToDateRange(): string {
  if (!overview.value) return ''
  const start = new Date(overview.value.period_start)
  const end = new Date(overview.value.period_end)
  const startMonth = start.toLocaleString('en-US', { month: 'long' })
  const endMonth = end.toLocaleString('en-US', { month: 'long' })
  if (start.getMonth() === end.getMonth() && start.getFullYear() === end.getFullYear()) {
    return `${startMonth} ${start.getDate()} - ${end.getDate()}, ${end.getFullYear()}`
  }
  return `${startMonth} ${start.getDate()}, ${start.getFullYear()} - ${endMonth} ${end.getDate()}, ${end.getFullYear()}`
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    paid: 'Paga',
    pending: 'Pendente',
    overdue: 'Atrasada',
    cancelled: 'Cancelada',
    draft: 'Rascunho',
  }
  return map[status] ?? status
}

function statusColor(status: string): string {
  if (status === 'paid') return 'green'
  if (status === 'overdue') return 'red'
  if (status === 'cancelled') return 'grey'
  return 'orange'
}

function methodIcon(method: BillingPaymentMethodResponse): string {
  const key = (method.brand || method.billing_type || '').toUpperCase()
  if (key.includes('VISA')) return visaIcon
  if (key.includes('MASTER')) return mastercardIcon
  if (key.includes('AMEX') || key.includes('AMERICAN')) return amexIcon
  if (key.includes('PIX')) return pixIcon
  if (key.includes('BOLETO')) return boletoIcon
  return cardIcon
}

function methodLabel(method: BillingPaymentMethodResponse): string {
  if (method.billing_type === 'CREDIT_CARD' && method.last4) {
    const brand = method.brand || 'Cartão'
    return `${brand} final ${method.last4}`
  }
  return method.billing_type || 'Método'
}

function serviceAmount(row: BillingChargeLine): string {
  if (row.included) return 'Sem custo'
  if (!row.enabled) return 'Desativado'
  return formatCurrency(row.amount)
}

function toggleUsersExpansion() {
  usersExpanded.value = !usersExpanded.value
}

function toggleServicesExpansion() {
  servicesExpanded.value = !servicesExpanded.value
}

function expandAll() {
  const next = !allExpanded.value
  usersExpanded.value = next
  servicesExpanded.value = next
}

function goToHistory() {
  activeTab.value = 'history'
}

function goToUsers() {
  void router.push({ name: 'users' })
}

function openPayment(method?: BillingPaymentMethodResponse) {
  if (method) {
    selectedMethodId.value = method.id
    selectedPaymentType.value = method.billing_type || 'CREDIT_CARD'
  }
  showPaymentModal.value = true
}

function handleCustomAmountUpdate(val: string | number | null) {
  const valStr = String(val || '0')
  const num = parseFloat(valStr.replace(',', '.'))
  if (!Number.isNaN(num)) {
    customAmount.value = num
    customAmountDisplay.value = num.toFixed(2).replace('.', ',')
  }
}

async function loadOverview() {
  const { data } = await billingApi.overview()
  overview.value = data
  customAmount.value = money(data.total)
  customAmountDisplay.value = money(data.total).toFixed(2).replace('.', ',')
}

async function loadInvoices() {
  const { data } = await billingApi.invoices()
  invoices.value = data
}

async function loadPaymentMethods() {
  paymentMethodsError.value = null
  loadingPaymentMethods.value = true
  try {
    const { data } = await billingApi.paymentMethods()
    paymentMethods.value = data
    if (!data.length) paymentMethodsError.value = 'NO_PAYMENT_METHODS'
    if (data.length && !selectedMethodId.value) {
      selectedMethodId.value = data.find((method) => method.is_primary)?.id ?? data[0].id
    }
  } catch (error) {
    paymentMethodsError.value = apiErrorMessage(error, 'Não foi possível carregar os métodos')
    paymentMethods.value = []
  } finally {
    loadingPaymentMethods.value = false
  }
}

async function loadSettings() {
  settingsError.value = null
  loadingSettings.value = true
  try {
    const { data } = await billingApi.settings()
    settings.value = data
  } catch (error) {
    settingsError.value = apiErrorMessage(error, 'Não foi possível carregar as configurações')
  } finally {
    loadingSettings.value = false
  }
}

async function refresh() {
  loading.value = true
  lastUpdate.value = new Date()
  try {
    await Promise.all([loadOverview(), loadInvoices(), loadPaymentMethods(), loadSettings()])
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Falha ao atualizar o faturamento') })
  } finally {
    loading.value = false
  }
}

async function applyPromo() {
  if (!canUpdateSettings.value || !promoCode.value.trim()) return
  try {
    const { data } = await billingApi.applyPromo(promoCode.value)
    settings.value = data
    promoCode.value = ''
    await loadOverview()
    $q.notify({ type: 'positive', message: 'Código promocional aplicado' })
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Código inválido') })
  }
}

async function submitPayment() {
  if (!canPay.value) return
  paying.value = true
  try {
    const amount = paymentAmount.value === 'custom' ? customAmount.value : money(overview.value?.total)
    const { data } = await billingApi.createPayment({
      billing_type: selectedPaymentType.value,
      payment_method_id: selectedMethodId.value ?? undefined,
      amount,
    })
    showPaymentModal.value = false
    if (data.invoice_url) {
      window.open(data.invoice_url, '_blank', 'noopener')
    }
    $q.notify({ type: 'positive', message: 'Cobrança gerada' })
    await Promise.all([loadOverview(), loadInvoices()])
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Não foi possível gerar a cobrança') })
  } finally {
    paying.value = false
  }
}

async function addCard() {
  if (!canManageMethods.value) return
  const [month, year] = newCard.value.expiry.split('/')
  savingCard.value = true
  try {
    await billingApi.addPaymentMethod({
      billing_type: 'CREDIT_CARD',
      holder_name: newCard.value.holder_name,
      card_number: newCard.value.card_number.replace(/\s/g, ''),
      expiry_month: month,
      expiry_year: year,
      ccv: newCard.value.ccv,
      last4: newCard.value.card_number.replace(/\s/g, '').slice(-4),
      is_primary: paymentMethods.value.length === 0,
    })
    showAddCardModal.value = false
    newCard.value = { holder_name: '', card_number: '', expiry: '', ccv: '' }
    await loadPaymentMethods()
    $q.notify({ type: 'positive', message: 'Método de pagamento salvo' })
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Não foi possível salvar o cartão') })
  } finally {
    savingCard.value = false
  }
}

async function saveCycle(day: number) {
  if (!canUpdateSettings.value) return
  savingSettings.value = true
  try {
    const { data } = await billingApi.updateSettings({ cycle_close_day: day })
    settings.value = data
    await loadOverview()
    $q.notify({ type: 'positive', message: 'Dia de fechamento atualizado' })
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Não foi possível salvar') })
  } finally {
    savingSettings.value = false
  }
}

async function toggleAlert() {
  if (!canUpdateSettings.value || !settings.value) return
  const { data } = await billingApi.updateSettings({ alert_enabled: !settings.value.alert_enabled })
  settings.value = data
}

async function saveAddress() {
  if (!canUpdateSettings.value || !settings.value) return
  savingSettings.value = true
  try {
    const { data } = await billingApi.updateSettings({
      legal_name: settings.value.legal_name,
      email: settings.value.email,
      cpf_cnpj: settings.value.cpf_cnpj,
      postal_code: settings.value.postal_code,
      address: settings.value.address,
      address_number: settings.value.address_number,
      complement: settings.value.complement,
      province: settings.value.province,
      city: settings.value.city,
      state: settings.value.state,
      country: settings.value.country,
    })
    settings.value = data
    showAddressModal.value = false
    $q.notify({ type: 'positive', message: 'Endereço atualizado' })
  } catch (error) {
    $q.notify({ type: 'negative', message: apiErrorMessage(error, 'Não foi possível salvar o endereço') })
  } finally {
    savingSettings.value = false
  }
}

async function lookupCep() {
  const cep = (settings.value?.postal_code || '').replace(/\D/g, '')
  if (cep.length !== 8 || !settings.value) return
  try {
    const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`)
    const data = (await response.json()) as {
      erro?: boolean
      logradouro?: string
      complemento?: string
      bairro?: string
      localidade?: string
      uf?: string
    }
    if (data.erro) return
    settings.value.address = data.logradouro || settings.value.address
    settings.value.complement = data.complemento || settings.value.complement
    settings.value.province = data.bairro || settings.value.province
    settings.value.city = data.localidade || settings.value.city
    settings.value.state = data.uf || settings.value.state
    settings.value.country = 'Brasil'
  } catch {
    // ViaCEP is best-effort
  }
}

async function downloadInvoice(invoice: BillingInvoiceResponse) {
  if (invoice.invoice_url) {
    window.open(invoice.invoice_url, '_blank', 'noopener')
    return
  }
  if (!canExport.value) return
  const { data } = await billingApi.exportInvoice(invoice.id)
  const url = URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = `fatura-${invoice.id}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

async function downloadSummary() {
  const latest = invoices.value[0]
  if (latest) {
    await downloadInvoice(latest)
    return
  }
  $q.notify({ type: 'info', message: 'Nenhuma fatura disponível para download' })
}

function payWithType(type: string) {
  selectedPaymentType.value = type
  selectedMethodId.value = null
  void submitPayment()
}

onMounted(() => {
  void refresh()
})
</script>

<template>
  <q-page class="billing-page">
    <q-card class="billing-header-card" flat>
      <q-card-section class="billing-header-section">
        <div class="billing-header">
          <div class="billing-header__copy">
            <h1 class="billing-title">Faturamento</h1>
            <div class="billing-updated">
              <p class="billing-updated__text">{{ formatLastUpdate() }}</p>
              <q-btn
                flat
                round
                dense
                no-caps
                icon="refresh"
                size="sm"
                class="billing-updated__refresh"
                :loading="loading"
                @click="refresh"
              />
            </div>
          </div>
          <div class="billing-header__actions">
            <q-btn
              outline
              no-caps
              icon="open_in_new"
              label="Como funciona o faturamento"
              class="billing-action-btn billing-action-btn--outline"
            />
            <q-btn
              v-if="canPay"
              unelevated
              no-caps
              icon="monetization_on"
              label="Fazer um pagamento"
              class="billing-action-btn billing-action-btn--primary"
              @click="openPayment()"
            />
          </div>
        </div>
      </q-card-section>

      <div class="billing-tabs">
        <q-tabs
          v-model="activeTab"
          no-caps
          align="left"
          narrow-indicator
          active-color="primary"
          indicator-color="primary"
          class="billing-tabs__bar"
        >
          <q-tab name="overview" label="Visão Geral" />
          <q-tab name="history" label="Histórico" />
          <q-tab name="settings" label="Configurações" />
        </q-tabs>
      </div>
    </q-card>

    <q-card class="billing-body-card" flat>
      <q-card-section class="billing-body-section">
        <q-tab-panels v-model="activeTab" animated class="billing-panels">
          <q-tab-panel name="overview" class="billing-panel">
            <q-card class="estimated-due-card" flat>
              <q-card-section class="estimated-due-section">
                <h2 class="estimated-due-title">Valor Estimado</h2>
                <div class="estimated-due-amount">{{ formatCurrency(overview?.total) }}</div>
                <p class="estimated-due-copy">
                  Esta é uma estimativa do valor que você deve com base no uso do mês até a data, após créditos, pré-pagamentos e descontos.
                </p>

                <q-separator class="estimated-due-divider" />

                <div class="billing-metrics">
                  <div class="billing-metric">
                    <div class="billing-metric__label">Vencimento</div>
                    <div class="billing-metric__value">{{ formatDate(overview?.payment_due) }}</div>
                  </div>
                  <div class="billing-metric">
                    <div class="billing-metric__label">Pré-pagamentos</div>
                    <div class="billing-metric__value">{{ formatCurrency(overview?.prepayments) }}</div>
                  </div>
                  <div class="billing-metric">
                    <div class="billing-metric__label">Desconto</div>
                    <div class="billing-metric__value billing-metric__value--negative">{{ formatDiscount(overview?.discount) }}</div>
                  </div>
                  <div class="billing-metric">
                    <div class="billing-metric__label">Uso total</div>
                    <div class="billing-metric__value">{{ formatCurrency(overview?.subtotal) }}</div>
                  </div>
                </div>
              </q-card-section>
            </q-card>

            <q-card class="month-summary-card border border-gray-200 shadow-none mt-8" style="background-color: var(--app-content-background, #ffffff);">
              <q-card-section class="p-8">
                <div class="month-summary-header flex justify-between items-start mb-6">
                  <div class="month-summary-title-section flex-1">
                    <h2 class="text-2xl font-semibold mb-2" style="color: var(--q-primary, #1e40af);">Resumo do mês {{ monthToDateRange() }}</h2>
                    <p class="text-gray-500 text-sm mb-0">{{ overview?.days_elapsed ?? 0 }} dia(s) decorridos neste ciclo.</p>
                  </div>
                  <div class="summary-actions flex gap-4 items-start">
                    <q-btn
                      unelevated
                      no-caps
                      class="summary-btn h-10"
                      icon="expand_more"
                      label="Download"
                      style="background-color: var(--q-primary, #1e40af); color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"
                      @click="downloadSummary"
                    />
                    <q-btn
                      unelevated
                      no-caps
                      class="summary-btn h-10"
                      :label="allExpanded ? 'Recolher tudo' : 'Expandir tudo'"
                      style="background-color: var(--q-primary, #1e40af); color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"
                      @click="expandAll"
                    />
                  </div>
                </div>

                <table class="charges-table w-full border-collapse mb-6">
                  <tbody>
                    <tr class="border-t border-b border-gray-100">
                      <td class="py-4 align-middle">
                        <div class="charge-item flex items-center gap-3">
                          <q-icon
                            :name="usersExpanded ? 'expand_less' : 'expand_more'"
                            class="charge-icon text-gray-500 text-sm cursor-pointer"
                            @click="toggleUsersExpansion"
                          />
                          <span class="charge-description font-medium">Usuários ({{ users.length }})</span>
                          <q-btn
                            v-if="canViewUsers"
                            flat
                            dense
                            class="charge-link underline text-sm ml-2"
                            style="color: var(--q-primary, #1e40af);"
                            label="Ver usuários"
                            @click="goToUsers"
                          />
                        </div>
                      </td>
                      <td class="charge-amount text-right font-semibold">{{ formatCurrency(usersTotal) }}</td>
                    </tr>
                    <template v-if="usersExpanded">
                      <tr>
                        <td colspan="2" class="p-0">
                          <q-table
                            :rows="users"
                            :columns="usersColumns"
                            row-key="ref"
                            flat
                            :pagination="usersPagination"
                            :rows-per-page-options="[5, 10, 15, 25, 50, 100]"
                            class="users-billing-table"
                            hide-header
                            @update:pagination="usersPagination = $event"
                          >
                            <template #body-cell-user="props">
                              <q-td :props="props" class="py-3 text-sm text-gray-600 bg-gray-50 user-cell">
                                <div class="flex items-center gap-2" style="padding-left: 0.85rem;">
                                  <q-icon name="subdirectory_arrow_right" class="text-gray-500 text-sm" size="18px" />
                                  <span>{{ props.row.label }}</span>
                                </div>
                              </q-td>
                            </template>
                            <template #body-cell-detail="props">
                              <q-td :props="props" class="py-3 pl-12 text-sm text-gray-600 bg-gray-50">
                                {{ formatCurrency(props.row.unit_amount) }} / mês
                              </q-td>
                            </template>
                            <template #body-cell-cost="props">
                              <q-td :props="props" class="py-3 text-sm text-gray-600 bg-gray-50 cost-cell">
                                {{ formatCurrency(props.value) }}
                              </q-td>
                            </template>
                          </q-table>
                        </td>
                      </tr>
                    </template>
                    <tr class="border-b border-gray-100">
                      <td class="py-4 align-middle">
                        <div class="charge-item flex items-center gap-3">
                          <q-icon
                            :name="servicesExpanded ? 'expand_less' : 'expand_more'"
                            class="charge-icon text-gray-500 text-sm cursor-pointer"
                            @click="toggleServicesExpansion"
                          />
                          <span class="charge-description font-medium">Serviços ({{ services.length }})</span>
                        </div>
                      </td>
                      <td class="charge-amount text-right font-semibold">{{ formatCurrency(servicesTotal) }}</td>
                    </tr>
                    <template v-if="servicesExpanded">
                      <tr>
                        <td colspan="2" class="p-0">
                          <q-table
                            :rows="services"
                            :columns="servicesColumns"
                            row-key="ref"
                            flat
                            :pagination="servicesPagination"
                            :rows-per-page-options="[5, 10, 15, 25, 50, 100]"
                            class="services-billing-table"
                            hide-header
                            @update:pagination="servicesPagination = $event"
                          >
                            <template #body-cell-service="props">
                              <q-td :props="props" class="py-3 text-sm text-gray-600 bg-gray-50 service-cell">
                                <div class="flex items-center gap-2" style="padding-left: 0.85rem;">
                                  <q-icon name="subdirectory_arrow_right" class="text-gray-500 text-sm" size="18px" />
                                  <span>{{ props.row.label }}</span>
                                </div>
                              </q-td>
                            </template>
                            <template #body-cell-cost="props">
                              <q-td :props="props" class="py-3 text-sm text-gray-600 bg-gray-50 cost-cell">
                                <span v-if="props.row.included" class="text-gray-500">Sem custo</span>
                                <span v-else-if="!props.row.enabled" class="text-gray-500">Desativado</span>
                                <span v-else>{{ formatCurrency(props.value) }}</span>
                              </q-td>
                            </template>
                          </q-table>
                        </td>
                      </tr>
                    </template>
                  </tbody>
                </table>

                <table class="w-full border-collapse bg-white" style="table-layout: fixed;">
                  <colgroup>
                    <col style="width: 50%;">
                    <col style="width: 25%;">
                    <col style="width: 25%;">
                  </colgroup>
                  <tbody>
                    <tr>
                      <td></td>
                      <td class="py-2 pl-4">
                        <span class="total-label font-medium">Subtotal</span>
                      </td>
                      <td class="py-2 text-right">
                        <span class="total-amount font-semibold">{{ formatCurrency(overview?.subtotal) }}</span>
                      </td>
                    </tr>
                    <tr>
                      <td></td>
                      <td class="py-2 pl-4">
                        <span class="total-label">Desconto</span>
                      </td>
                      <td class="py-2 text-right">
                        <span class="total-amount" style="color: #dc2626;">{{ formatCurrency(overview?.discount) }}</span>
                      </td>
                    </tr>
                    <tr>
                      <td></td>
                      <td class="py-2 pl-4">
                        <span class="total-label font-bold text-lg" style="color: var(--q-primary, #1e40af);">Total</span>
                      </td>
                      <td class="py-2 text-right">
                        <span class="total-amount font-bold text-lg" style="color: var(--q-primary, #1e40af);">{{ formatCurrency(overview?.total) }}</span>
                      </td>
                    </tr>
                  </tbody>
                </table>

                <p class="mt-6">
                  Ver faturas anteriores
                  <q-btn
                    flat
                    dense
                    class="billing-history-link underline text-sm"
                    style="color: var(--q-primary, #1e40af);"
                    label="Histórico de faturamento"
                    @click="goToHistory"
                  />
                </p>
              </q-card-section>
            </q-card>

            <q-card class="payment-methods-card border border-gray-200 shadow-none mt-8" style="background-color: var(--app-content-background, #ffffff);">
              <q-card-section class="p-8">
                <div class="payment-methods-title flex justify-between items-center mb-8">
                  <h2 class="text-2xl font-semibold mb-0" style="color: var(--q-primary, #1e40af);">Métodos de pagamento</h2>
                  <q-btn
                    v-if="canManageMethods"
                    unelevated
                    class="add-payment-btn h-10"
                    label="Adicionar método"
                    style="background-color: var(--q-primary, #1e40af); color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"
                    @click="showAddCardModal = true"
                  />
                </div>

                <div class="payment-section">
                  <h3 class="payment-section-title">Principal</h3>
                  <p class="payment-section-description">
                    Usado automaticamente no vencimento do ciclo.
                  </p>

                  <div v-if="loadingPaymentMethods" class="payment-method-loading text-sm leading-relaxed">
                    <q-spinner size="20px" />
                    <span class="ml-2 text-gray-500">Carregando métodos de pagamento</span>
                  </div>
                  <div v-else-if="paymentMethodsError === 'NO_PAYMENT_METHODS'" class="payment-method-error text-sm leading-relaxed">
                    <p class="text-red-600 mb-2">Nenhum método de pagamento cadastrado.</p>
                  </div>
                  <div v-else-if="paymentMethodsError" class="payment-method-error text-sm leading-relaxed text-red-600">
                    {{ paymentMethodsError }}
                  </div>
                  <div v-else-if="paymentMethods.length > 0">
                    <q-card
                      v-for="method in paymentMethods"
                      :key="method.id"
                      class="payment-method-card border border-gray-200 shadow-none mb-4"
                      style="background-color: var(--app-content-background, #ffffff);"
                    >
                      <q-card-section class="p-3">
                        <div class="flex items-center justify-between">
                          <div class="payment-method-info flex items-center gap-4">
                            <div class="payment-method-logo w-16 h-10 flex items-center justify-center">
                              <img
                                :src="methodIcon(method)"
                                :alt="methodLabel(method)"
                                class="w-full h-full object-contain"
                              />
                            </div>
                            <div class="payment-method-details">
                              <span class="payment-method-text font-medium text-sm" style="color: var(--q-primary, #1e40af);">{{ methodLabel(method) }}</span>
                            </div>
                          </div>
                          <q-btn flat round dense icon="more_vert" class="payment-method-menu text-gray-500">
                            <q-menu>
                              <q-list style="min-width: 150px">
                                <q-item
                                  v-if="canManageMethods"
                                  v-close-popup
                                  clickable
                                  class="payment-menu-item"
                                  @click="showAddCardModal = true"
                                >
                                  <q-item-section>Atualizar cartão</q-item-section>
                                </q-item>
                                <q-item
                                  v-if="canPay"
                                  v-close-popup
                                  clickable
                                  class="payment-menu-item"
                                  @click="openPayment(method)"
                                >
                                  <q-item-section>Fazer pagamento</q-item-section>
                                </q-item>
                              </q-list>
                            </q-menu>
                          </q-btn>
                        </div>
                      </q-card-section>
                    </q-card>
                  </div>
                  <div v-else class="payment-method-error text-sm leading-relaxed">
                    <p class="text-red-600 mb-2">Nenhum método de pagamento cadastrado.</p>
                  </div>
                </div>

                <div class="payment-section payment-section--last">
                  <h3 class="payment-section-title">Reserva</h3>
                  <p class="payment-section-description">
                    Usado se o método principal falhar.
                  </p>
                  <q-banner class="backup-info-box" dense>
                    <template #avatar>
                      <q-icon name="info" class="info-icon text-xl" style="color: var(--q-primary, #1e40af);" />
                    </template>
                    <span class="backup-info-text text-sm" style="color: var(--q-primary, #1e40af);">Nenhum método de reserva cadastrado.</span>
                  </q-banner>
                </div>
              </q-card-section>
            </q-card>

            <q-card class="promos-card border border-gray-200 shadow-none mt-8" style="background-color: var(--app-content-background, #ffffff);">
              <q-card-section class="p-8">
                <div class="promos-header">
                  <div class="promos-title-section">
                    <h2 class="promos-title">Promoções</h2>
                    <h3 class="promo-code-title">Código promocional</h3>
                    <p class="promo-description">
                      Aplique um código promocional ao ciclo atual.
                    </p>
                    <q-btn
                      flat
                      dense
                      class="promo-link underline text-sm inline-flex items-center gap-1"
                      style="color: var(--q-primary, #1e40af);"
                      label="Saiba mais sobre códigos promocionais"
                      icon-right="open_in_new"
                    />
                  </div>
                  <div class="promo-actions flex items-start">
                    <q-btn
                      v-if="canUpdateSettings"
                      unelevated
                      class="apply-code-btn whitespace-nowrap h-10"
                      label="Aplicar código"
                      style="background-color: var(--q-primary, #1e40af); color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"
                      @click="applyPromo"
                    />
                  </div>
                </div>

                <div class="promo-form">
                  <q-input
                    v-model="promoCode"
                    placeholder="Adicionar novo código"
                    outlined
                  />
                  <p v-if="overview?.promo_code" class="mt-2 text-sm" style="color: var(--q-primary, #1e40af);">
                    Código ativo: {{ overview.promo_code }}
                  </p>
                </div>
              </q-card-section>
            </q-card>
          </q-tab-panel>

          <q-tab-panel name="history" class="billing-panel">
            <q-card class="settings-card" flat>
              <q-card-section>
                <h2 class="settings-card-title">Histórico de faturamento</h2>
                <p class="settings-description">
                  Faturas geradas para esta tenant.
                </p>

                <q-table
                  :rows="invoices"
                  :columns="historyColumns"
                  row-key="id"
                  flat
                  class="billing-history-table"
                >
                  <template #body-cell-date="props">
                    <q-td :props="props">{{ formatDate(props.row.created_at) }}</q-td>
                  </template>
                  <template #body-cell-amount="props">
                    <q-td :props="props">{{ formatCurrency(props.row.total) }}</q-td>
                  </template>
                  <template #body-cell-status="props">
                    <q-td :props="props">
                      <q-badge :color="statusColor(props.value)" :label="statusLabel(props.value)" />
                    </q-td>
                  </template>
                  <template #body-cell-invoice="props">
                    <q-td :props="props" class="!text-right !flex !justify-end">
                      <q-btn
                        v-if="canExport || props.row.invoice_url"
                        flat
                        outline
                        size="sm"
                        label="Baixar"
                        style="color: var(--q-primary, #1e40af);"
                        @click="downloadInvoice(props.row)"
                      />
                    </q-td>
                  </template>
                  <template #no-data>
                    <div class="full-width text-center text-grey-7 q-pa-md">Nenhuma fatura ainda.</div>
                  </template>
                </q-table>
              </q-card-section>
            </q-card>
          </q-tab-panel>

          <q-tab-panel name="settings" class="billing-panel">
            <q-card class="settings-card" flat>
              <q-card-section>
                <div class="settings-grid">
                  <div class="settings-grid__title">
                    <h2 class="settings-card-title">Informações de endereço</h2>
                  </div>
                  <div class="settings-grid__body">
                    <div class="settings-section">
                      <p class="settings-description">
                        Usadas nas faturas e no cadastro Asaas da tenant.
                      </p>
                      <div v-if="loadingSettings" class="settings-address text-sm leading-relaxed">
                        <q-spinner size="20px" />
                        <span class="ml-2 text-gray-500">Carregando endereço</span>
                      </div>
                      <div v-else-if="settingsError" class="settings-address text-sm leading-relaxed text-red-600">
                        {{ settingsError }}
                      </div>
                      <div v-else-if="hasAddress && settings" class="settings-address text-sm leading-relaxed">
                        <div>
                          <span v-if="settings.address_number">{{ settings.address }}, {{ settings.address_number }}</span>
                          <span v-else>{{ settings.address }}</span>
                          <span v-if="settings.complement"> - {{ settings.complement }}</span>
                        </div>
                        <div v-if="settings.province">{{ settings.province }}</div>
                        <div v-if="settings.city && settings.state">
                          {{ settings.city }}, {{ settings.state }}<span v-if="settings.postal_code"> - {{ settings.postal_code }}</span>
                        </div>
                        <div v-if="settings.country">{{ settings.country }}</div>
                      </div>
                      <div v-else class="settings-address text-sm leading-relaxed">
                        <p class="text-red-600 mb-2">Endereço não cadastrado.</p>
                      </div>
                    </div>

                    <div class="settings-section settings-section--last">
                      <q-separator class="settings-divider" />
                      <h3 class="settings-section-title">Local tributário</h3>
                      <p class="settings-description">
                        Impostos são calculados com base no endereço de faturamento.
                      </p>
                      <p class="settings-description settings-description--last">
                        Impostos não são recolhidos automaticamente neste ciclo.
                      </p>
                    </div>
                  </div>
                  <div class="settings-grid__action">
                    <q-btn
                      v-if="canUpdateSettings"
                      flat
                      dense
                      no-caps
                      class="settings-edit-link"
                      label="Editar"
                      @click="showAddressModal = true"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>

            <q-card class="settings-card" flat>
              <q-card-section>
                <div class="settings-grid">
                  <div class="settings-grid__title">
                    <h2 class="settings-card-title">Dia de fechamento do ciclo</h2>
                  </div>
                  <div class="settings-grid__body">
                    <p class="settings-description">
                      Define o recorte do valor estimado e o vencimento.
                    </p>
                    <div class="settings-cycle-close-day mb-4">
                      <q-btn-toggle
                        :model-value="settings?.cycle_close_day ?? 9"
                        :options="cycleOptions"
                        toggle-color="primary"
                        color="white"
                        text-color="primary"
                        class="cycle-close-day-toggle"
                        :disable="!canUpdateSettings || savingSettings"
                        @update:model-value="saveCycle"
                      />
                    </div>
                  </div>
                  <div class="settings-grid__action"></div>
                </div>
              </q-card-section>
            </q-card>

            <q-card class="settings-card" flat>
              <q-card-section>
                <div class="settings-grid">
                  <div class="settings-grid__title">
                    <h2 class="settings-card-title">Alerta de faturamento</h2>
                  </div>
                  <div class="settings-grid__body">
                    <p class="settings-description">
                      Receba um aviso quando o ciclo estiver próximo do fechamento.
                    </p>
                    <div class="settings-status">
                      <span class="settings-status-label">Status:</span>
                      <span
                        class="settings-status-value"
                        :class="settings?.alert_enabled ? 'is-on' : 'is-off'"
                      >
                        {{ settings?.alert_enabled ? 'Ativado' : 'Desativado' }}
                      </span>
                    </div>
                  </div>
                  <div class="settings-grid__action">
                    <q-btn
                      v-if="canUpdateSettings"
                      flat
                      dense
                      no-caps
                      class="settings-edit-link"
                      :label="settings?.alert_enabled ? 'Desativar alerta' : 'Ativar alerta'"
                      @click="toggleAlert"
                    />
                  </div>
                </div>
              </q-card-section>
            </q-card>

            <q-card class="settings-card settings-card--last" flat>
              <q-card-section>
                <div class="settings-grid">
                  <div class="settings-grid__title">
                    <h2 class="settings-card-title">Plano e serviços contratados</h2>
                  </div>
                  <div class="settings-grid__body">
                    <div class="settings-plan-info">
                      <div
                        v-for="service in contractedServices"
                        :key="service.ref || service.label"
                        class="settings-plan-row"
                      >
                        <q-badge
                          :label="service.label"
                          class="settings-plan-badge"
                        />
                        <div class="settings-plan-price">
                          {{ serviceAmount(service) }}
                        </div>
                      </div>
                    </div>
                    <p class="settings-description settings-description--last">
                      Serviços ativos desta tenant. Alterações de contrato são feitas pela plataforma.
                    </p>
                  </div>
                  <div class="settings-grid__action"></div>
                </div>
              </q-card-section>
            </q-card>
          </q-tab-panel>
        </q-tab-panels>
      </q-card-section>
    </q-card>

    <q-dialog v-model="showPaymentModal" class="make-payment-drawer">
      <q-card class="drawer-card fixed top-0 right-0" style="width: 500px; max-width: 100vw; height: 100vh; z-index: 9999;">
        <div class="drawer-container">
          <q-scroll-area class="drawer-scroll">
            <div class="drawer-body">
              <div class="drawer-header">
                <div class="drawer-header__title">
                  <div class="drawer-icon">
                    <q-icon name="monetization_on" size="24px" color="white" />
                  </div>
                  <h3 class="drawer-title">Fazer um pagamento</h3>
                </div>
                <q-btn flat round dense icon="close" @click="showPaymentModal = false" />
              </div>

              <q-banner class="payment-info-banner" dense>
                O valor estimado deste ciclo é {{ formatCurrency(overview?.total) }}.
              </q-banner>

              <div class="drawer-section">
                <h6 class="drawer-section-title">Valor do pagamento</h6>
                <div class="payment-amount-options">
                  <q-card
                    class="payment-option-card"
                    :class="{ 'is-selected': paymentAmount === 'estimated' }"
                    flat
                    @click="paymentAmount = 'estimated'"
                  >
                    <q-card-section class="payment-option-card__body">
                      <q-radio v-model="paymentAmount" val="estimated" />
                      <span class="payment-option-label">Valor estimado ({{ formatCurrency(overview?.total) }})</span>
                    </q-card-section>
                  </q-card>
                  <q-card
                    class="payment-option-card"
                    :class="{ 'is-selected': paymentAmount === 'custom' }"
                    flat
                    @click="paymentAmount = 'custom'"
                  >
                    <q-card-section class="payment-option-card__body">
                      <q-radio v-model="paymentAmount" val="custom" />
                      <span class="payment-option-label">Outro valor</span>
                    </q-card-section>
                  </q-card>
                </div>

                <q-card v-if="paymentAmount === 'custom'" class="custom-amount-field" flat>
                  <q-card-section>
                    <q-input
                      v-model="customAmountDisplay"
                      type="text"
                      label="Valor"
                      outlined
                      @update:model-value="handleCustomAmountUpdate"
                    />
                  </q-card-section>
                </q-card>
              </div>

              <q-card class="payment-methods-card border border-gray-200 shadow-none" style="background-color: var(--app-content-background, #ffffff);">
                <q-card-section class="p-6">
                  <div class="payment-methods-header">
                    <h6 class="drawer-section-title">Métodos de pagamento</h6>
                    <q-btn
                      v-if="canManageMethods"
                      outline
                      class="add-payment-method-btn"
                      style="border-color: var(--q-primary, #1e40af); color: var(--q-primary, #1e40af);"
                      label="Adicionar método"
                      @click="showAddCardModal = true"
                    />
                  </div>

                  <div v-if="loadingPaymentMethods" class="payment-method-loading text-sm leading-relaxed mb-6">
                    <q-spinner size="20px" />
                    <span class="ml-2 text-gray-500">Carregando métodos de pagamento</span>
                  </div>
                  <div v-else-if="paymentMethodsError === 'NO_PAYMENT_METHODS'" class="payment-method-error text-sm leading-relaxed mb-6">
                    <p class="text-red-600 mb-2">Nenhum método de pagamento cadastrado.</p>
                  </div>
                  <div v-else-if="paymentMethodOptions.length > 0">
                    <div class="saved-payment-methods text-sm font-medium text-gray-500 mb-3">Métodos salvos</div>
                    <div class="custom-payment-dropdown relative mb-6">
                      <q-select
                        v-model="selectedMethodId"
                        :options="paymentMethodOptions"
                        outlined
                        emit-value
                        map-options
                        option-label="label"
                        option-value="value"
                        @update:model-value="selectedPaymentType = 'CREDIT_CARD'"
                      >
                        <template #selected>
                          <div v-if="selectedMethodId" class="flex items-center gap-2">
                            <div
                              v-if="paymentMethodOptions.find((opt) => opt.value === selectedMethodId)"
                              class="payment-method-logo relative w-16 h-10 flex items-center justify-center"
                            >
                              <img
                                :src="methodIcon(paymentMethodOptions.find((opt) => opt.value === selectedMethodId)?.method as BillingPaymentMethodResponse)"
                                alt=""
                                class="w-full h-full object-contain"
                              />
                            </div>
                            <span>{{ paymentMethodOptions.find((opt) => opt.value === selectedMethodId)?.label }}</span>
                          </div>
                          <span v-else class="text-gray-400">Selecione um método</span>
                        </template>
                        <template #option="scope">
                          <q-item v-bind="scope.itemProps">
                            <q-item-section avatar>
                              <div class="payment-method-logo relative w-12 h-8 flex items-center justify-center">
                                <img :src="methodIcon(scope.opt.method)" alt="" class="w-full h-full object-contain" />
                              </div>
                            </q-item-section>
                            <q-item-section>
                              <q-item-label>{{ scope.opt.label }}</q-item-label>
                            </q-item-section>
                          </q-item>
                        </template>
                      </q-select>
                    </div>
                  </div>

                  <q-btn
                    unelevated
                    class="submit-payment-btn w-full mb-4 h-10"
                    label="Enviar pagamento"
                    :loading="paying"
                    style="background-color: var(--q-primary, #1e40af); color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"
                    @click="submitPayment"
                  />

                  <div class="or-pay-with text-center text-gray-500 text-sm mb-4">ou pague com</div>

                  <q-btn
                    outline
                    class="w-full flex items-center justify-center gap-2 mb-3"
                    style="border-color: var(--q-primary, #1e40af); color: var(--q-primary, #1e40af);"
                    :loading="paying"
                    @click="payWithType('PIX')"
                  >
                    <img :src="pixIcon" alt="PIX" class="w-6 h-6 object-contain" />
                    PIX
                  </q-btn>
                  <q-btn
                    outline
                    class="w-full flex items-center justify-center gap-2"
                    style="border-color: var(--q-primary, #1e40af); color: var(--q-primary, #1e40af);"
                    :loading="paying"
                    @click="payWithType('BOLETO')"
                  >
                    <img :src="boletoIcon" alt="Boleto" class="w-6 h-6 object-contain" />
                    Boleto
                  </q-btn>
                </q-card-section>
              </q-card>
            </div>
          </q-scroll-area>
        </div>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showAddCardModal" class="edit-card-drawer">
      <q-card class="drawer-card fixed top-0 right-0" style="width: 500px; max-width: 100vw; height: 100vh; z-index: 9999;">
        <div class="drawer-container">
          <q-scroll-area class="drawer-scroll">
            <div class="drawer-body">
              <div class="drawer-header">
                <div class="drawer-header__title">
                  <div class="drawer-icon">
                    <q-icon name="credit_card" size="24px" color="white" />
                  </div>
                  <h3 class="drawer-title">Adicionar cartão</h3>
                </div>
                <q-btn flat round dense icon="close" @click="showAddCardModal = false" />
              </div>

              <div class="drawer-section">
                <h6 class="drawer-section-title">Dados do cartão</h6>
                <p class="drawer-copy">
                  Os dados do cartão são enviados ao Asaas e não ficam gravados aqui.
                </p>
                <div class="drawer-fields">
                  <q-input v-model="newCard.holder_name" label="Nome no cartão" outlined dense />
                  <q-input v-model="newCard.card_number" label="Número" outlined dense mask="#### #### #### ####" />
                  <div class="drawer-fields-row">
                    <q-input v-model="newCard.expiry" label="Validade" outlined dense mask="##/##" placeholder="MM/AA" />
                    <q-input v-model="newCard.ccv" label="CVV" outlined dense mask="####" />
                  </div>
                </div>
              </div>
            </div>
          </q-scroll-area>
          <div class="drawer-footer">
            <q-btn
              unelevated
              label="Salvar cartão"
              class="w-full h-10"
              :loading="savingCard"
              style="background-color: var(--q-primary, #1e40af); color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"
              @click="addCard"
            />
          </div>
        </div>
      </q-card>
    </q-dialog>

    <q-dialog v-model="showAddressModal" class="edit-card-drawer">
      <q-card class="drawer-card fixed top-0 right-0" style="width: 500px; max-width: 100vw; height: 100vh; z-index: 9999;">
        <div class="drawer-container">
          <q-scroll-area class="drawer-scroll">
            <div v-if="settings" class="drawer-body">
              <div class="drawer-header">
                <div class="drawer-header__title">
                  <div class="drawer-icon">
                    <q-icon name="location_on" size="24px" color="white" />
                  </div>
                  <h3 class="drawer-title">Editar endereço</h3>
                </div>
                <q-btn flat round dense icon="close" @click="showAddressModal = false" />
              </div>

              <div class="drawer-fields">
                <q-input v-model="settings.legal_name" label="Razão social" outlined dense />
                <q-input v-model="settings.email" label="E-mail" outlined dense />
                <q-input v-model="settings.cpf_cnpj" label="CPF / CNPJ" outlined dense />
                <q-input v-model="settings.postal_code" label="CEP" outlined dense @blur="lookupCep" />
                <q-input v-model="settings.address" label="Endereço" outlined dense />
                <q-input v-model="settings.address_number" label="Número" outlined dense />
                <q-input v-model="settings.complement" label="Complemento" outlined dense />
                <q-input v-model="settings.province" label="Bairro" outlined dense />
                <q-input v-model="settings.city" label="Cidade" outlined dense />
                <q-input v-model="settings.state" label="UF" outlined dense />
                <q-input v-model="settings.country" label="País" outlined dense />
              </div>
            </div>
          </q-scroll-area>
          <div class="drawer-footer">
            <q-btn
              unelevated
              label="Salvar endereço"
              class="w-full h-10"
              :loading="savingSettings"
              style="background-color: var(--q-primary, #1e40af); color: white; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"
              @click="saveAddress"
            />
          </div>
        </div>
      </q-card>
    </q-dialog>
  </q-page>
</template>

<style scoped>
.billing-page {
  min-height: 100%;
  padding: 0;
  background-color: var(--app-navigation-background, #f9fafb);
}

@media (min-width: 768px) {
  .billing-page {
    padding: 1rem;
  }
}

.billing-page :deep(.q-btn),
.billing-page :deep(.q-tab) {
  text-transform: none !important;
}

.billing-header-card,
.billing-body-card {
  box-shadow: none;
  background-color: var(--app-content-background, #ffffff);
}

.billing-header-card {
  border: 1px solid #e5e7eb;
  border-bottom: 0;
  border-radius: 0;
}

.billing-body-card {
  border: 1px solid #e5e7eb;
  border-radius: 0;
  margin-top: 0;
}

@media (min-width: 768px) {
  .billing-header-card {
    border-radius: 0.5rem 0.5rem 0 0;
  }

  .billing-body-card {
    border-radius: 0 0 0.5rem 0.5rem;
  }
}

.billing-header-card :deep(.billing-header-section) {
  padding: 2rem 2rem 0.25rem !important;
}

.billing-header {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem 2rem;
}

.billing-header__copy {
  flex: 1 1 16rem;
}

.billing-title {
  margin: 0;
  font-size: 2.25rem;
  font-weight: 700;
  line-height: 1.15;
  color: var(--q-primary, #1e40af);
}

.billing-updated {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.billing-updated__text {
  margin: 0;
  font-size: 0.875rem;
  color: #9ca3af;
}

.billing-updated__refresh {
  color: #4b5563;
}

.billing-header__actions {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 1rem;
}

.billing-action-btn {
  height: 40px;
  min-width: 240px;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.billing-action-btn--outline {
  border-color: var(--q-primary, #1e40af);
  color: var(--q-primary, #1e40af);
}

.billing-action-btn--primary {
  background-color: var(--q-primary, #1e40af);
  color: #ffffff;
}

.billing-tabs {
  padding: 0 2rem;
}

.billing-tabs__bar {
  color: #6b7280;
}

.billing-body-card :deep(.billing-body-section) {
  padding: 2rem !important;
}

.billing-panels,
.billing-panel,
.billing-page :deep(.q-tab-panels),
.billing-page :deep(.q-tab-panel) {
  padding: 0 !important;
  background: transparent;
}

.estimated-due-card {
  background-color: #eff6ff !important;
  border: 1px solid #bfdbfe;
  box-shadow: none;
  margin-bottom: 2rem;
}

.estimated-due-card :deep(.estimated-due-section) {
  padding: 2rem !important;
}

.estimated-due-title {
  margin: 0 0 1rem;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--q-primary, #1e40af);
}

.estimated-due-amount {
  margin-bottom: 1rem;
  font-size: 3rem;
  font-weight: 400;
  line-height: 1.1;
  color: var(--q-primary, #1e40af);
}

.estimated-due-copy {
  margin: 0 0 2rem;
  font-size: 0.875rem;
  line-height: 1.625;
  color: #6b7280;
}

.estimated-due-divider {
  margin: 1.5rem 0;
}

.billing-metrics {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 768px) {
  .billing-metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.billing-metric__label {
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.billing-metric__value {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--q-primary, #1e40af);
}

.billing-metric__value--negative {
  color: #dc2626;
}

.payment-methods-card :deep(h2),
.promos-title,
.settings-card-title {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
  line-height: 1.3;
  color: var(--q-primary, #1e40af);
}

.payment-section {
  margin-bottom: 2rem;
}

.payment-section--last {
  margin-bottom: 0;
}

.payment-section-title {
  margin: 0 0 0.5rem;
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #111827;
}

.payment-section-description,
.settings-description,
.promo-description,
.drawer-copy {
  margin: 0 0 1rem;
  font-size: 0.875rem;
  line-height: 1.625;
  color: #6b7280;
}

.settings-description--last {
  margin-bottom: 0;
}

.settings-address {
  font-size: 0.875rem;
  line-height: 1.625;
}

.settings-address .text-red-600,
.settings-address p {
  color: #dc2626;
  margin: 0 0 0.5rem;
}

.payment-method-error {
  font-size: 0.875rem;
  line-height: 1.625;
}

.payment-method-error p {
  margin: 0 0 0.5rem;
  color: #dc2626;
}

.backup-info-box {
  background-color: #eff6ff !important;
  border: 1px solid #bfdbfe;
  border-radius: 0.5rem;
  box-shadow: none;
}

.backup-info-text {
  font-size: 0.875rem;
  color: var(--q-primary, #1e40af);
}

.promos-title-section {
  flex: 1;
}

.promo-code-title {
  margin: 0 0 0.5rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--q-primary, #1e40af);
}

.promo-form {
  width: min(100%, 28rem);
  margin-top: 1rem;
}

.settings-card {
  border: 1px solid #e5e7eb;
  box-shadow: none;
  margin-bottom: 2rem;
  background-color: var(--app-content-background, #ffffff);
}

.settings-card--last {
  margin-bottom: 0;
}

.settings-card :deep(.q-card-section) {
  padding: 2rem !important;
}

.settings-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
}

@media (min-width: 768px) {
  .settings-grid {
    grid-template-columns: minmax(0, 3fr) minmax(0, 6fr) minmax(0, 3fr);
    gap: 1rem;
  }
}

.settings-card-title {
  margin-bottom: 0;
}

.settings-section {
  margin-bottom: 2rem;
  padding-bottom: 2rem;
}

.settings-section--last {
  margin-bottom: 0;
  padding-bottom: 0;
}

.settings-divider {
  margin: 0 0 2rem;
}

.settings-section-title {
  margin: 0 0 1rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--q-primary, #1e40af);
}

.settings-grid__action {
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
}

.settings-edit-link {
  color: var(--q-primary, #1e40af) !important;
  font-size: 0.875rem;
  font-weight: 500;
  text-decoration: none;
}

.settings-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1rem;
}

.settings-status-label,
.settings-status-value {
  font-size: 0.875rem;
  font-weight: 500;
}

.settings-status-label {
  color: #6b7280;
}

.settings-status-value.is-on {
  color: #16a34a;
}

.settings-status-value.is-off {
  color: #dc2626;
}

.settings-plan-row {
  margin-bottom: 0.5rem;
}

.settings-plan-badge {
  height: 1.5rem;
  line-height: 1.5rem;
  padding: 0 0.75rem;
  background-color: #3b82f6;
  color: #ffffff;
  font-size: 1.125rem;
  font-weight: 600;
}

.settings-plan-price {
  padding-left: 0.75rem;
  margin: 0.25rem 0 0.5rem;
  font-size: 0.875rem;
  color: #6b7280;
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.drawer-header__title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.drawer-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.25rem;
  background-color: #22c55e;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drawer-title {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--q-primary, #1e40af);
}

.drawer-body {
  padding: 1.5rem;
}

.drawer-section {
  margin-bottom: 2rem;
}

.drawer-section-title {
  margin: 0 0 1rem;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--q-primary, #1e40af);
}

.drawer-fields {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.drawer-fields-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.drawer-footer {
  padding: 1.5rem;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
}

.drawer-footer .q-btn {
  width: 100%;
  height: 40px;
  background-color: var(--q-primary, #1e40af);
  color: #ffffff;
}

.payment-info-banner {
  background-color: #fffbeb !important;
  border: 1px solid #fde68a;
  border-radius: 0.5rem;
  color: #dc2626;
  margin-bottom: 2rem;
  font-size: 0.875rem;
}

.payment-amount-options {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.payment-option-card {
  cursor: pointer;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  box-shadow: none;
}

.payment-option-card.is-selected {
  background-color: #eff6ff;
  border-color: var(--q-primary, #1e40af);
}

.payment-option-card__body {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem !important;
}

.payment-option-label {
  font-weight: 500;
}

.custom-amount-field {
  margin-top: 1rem;
  background-color: #f9fafb;
  border: 1px solid #e5e7eb;
}

.payment-methods-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.payment-methods-header .drawer-section-title {
  margin-bottom: 0;
}

.drawer-scroll {
  flex: 1;
  min-height: 0;
}

.month-summary-card,
.payment-methods-card,
.promos-card {
  border: 1px solid #e5e7eb;
  box-shadow: none;
  margin-top: 2rem;
  background-color: var(--app-content-background, #ffffff);
}

.month-summary-card :deep(h2) {
  margin: 0 0 0.5rem;
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--q-primary, #1e40af);
}

.month-summary-card :deep(.q-card-section),
.payment-methods-card :deep(.q-card-section),
.promos-card :deep(.q-card-section) {
  padding: 2rem;
}

.month-summary-header,
.payment-methods-title,
.promos-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.payment-methods-title {
  align-items: center;
  margin-bottom: 2rem;
}

.summary-actions,
.promo-actions {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.summary-btn,
.add-payment-btn,
.apply-code-btn {
  height: 40px;
  background-color: var(--q-primary, #1e40af) !important;
  color: #ffffff !important;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.1),
    0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.charges-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1.5rem;
}

.charge-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

:deep(.q-tabs) {
  margin-top: 0.5rem;
}

:deep(.q-tab) {
  padding: 1rem 1.5rem;
  color: #6b7280;
  font-weight: 500;
}

:deep(.q-tab--active) {
  color: var(--q-primary, #1e40af) !important;
}

:deep(.q-tabs__indicator) {
  background-color: var(--q-primary, #1e40af) !important;
}

.make-payment-drawer :deep(.q-dialog__inner),
.edit-card-drawer :deep(.q-dialog__inner) {
  padding: 0 !important;
  justify-content: flex-end !important;
  align-items: stretch !important;
}

.drawer-card {
  position: fixed !important;
  top: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15) !important;
  border-radius: 0 !important;
  background-color: white;
  height: 100vh !important;
  max-height: 100vh !important;
}

.drawer-container {
  height: 100%;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

:deep(.q-scrollarea) {
  flex: 1;
  min-height: 0;
}

@media (max-width: 768px) {
  .drawer-card {
    width: 100% !important;
    max-width: 100% !important;
  }
}

.billing-history-table :deep(.q-table__top) {
  display: none;
}

.billing-history-table :deep(.q-table thead th) {
  background-color: #f8f9fa;
  border-top: none;
  border-bottom: 1px solid #e5e7eb;
  color: #6b7280;
  font-weight: 500;
  font-size: 0.875rem;
}

.billing-history-table :deep(.q-table tbody td) {
  border-top: 1px solid #f3f4f6;
}

.users-billing-table :deep(.q-table__top),
.services-billing-table :deep(.q-table__top) {
  display: none;
}

.users-billing-table :deep(.q-table thead),
.services-billing-table :deep(.q-table thead) {
  display: none;
}

.users-billing-table :deep(.q-table tbody tr),
.services-billing-table :deep(.q-table tbody tr) {
  border-top: none !important;
}

.users-billing-table :deep(.q-table tbody td),
.services-billing-table :deep(.q-table tbody td) {
  border-top: none !important;
  border-bottom: 1px solid #f3f4f6;
}

.users-billing-table :deep(.q-table tbody tr:last-child td),
.services-billing-table :deep(.q-table tbody tr:last-child td) {
  border-bottom: none !important;
}

.users-billing-table :deep(.q-table__bottom),
.services-billing-table :deep(.q-table__bottom) {
  border-top: 1px solid #e5e7eb;
  padding: 1rem;
}

.users-billing-table :deep(.user-cell),
.services-billing-table :deep(.service-cell) {
  padding-left: 0.85rem !important;
}

.users-billing-table :deep(.cost-cell) {
  padding-right: 0.2rem !important;
  text-align: right !important;
}

.services-billing-table :deep(.cost-cell) {
  padding-right: 0.2rem !important;
}

.users-billing-table :deep(.q-table),
.services-billing-table :deep(.q-table) {
  table-layout: fixed !important;
}

.users-billing-table :deep(.q-table colgroup col:nth-child(1)) {
  width: 50% !important;
  min-width: 300px !important;
}

.users-billing-table :deep(.q-table colgroup col:nth-child(2)) {
  width: 25% !important;
  min-width: 100px !important;
}

.users-billing-table :deep(.q-table colgroup col:nth-child(3)) {
  width: 25% !important;
  min-width: 100px !important;
}

.services-billing-table :deep(.q-table colgroup col:nth-child(1)) {
  width: 75% !important;
  min-width: 300px !important;
}

.services-billing-table :deep(.q-table colgroup col:nth-child(2)) {
  width: 25% !important;
  min-width: 100px !important;
}

.backup-info-box :deep(.q-banner__content) {
  color: var(--q-primary, #1e40af);
}

:deep(.q-field--outlined .q-field__control) {
  background-color: #f8f9fa;
}

:deep(.q-field--outlined.q-field--focused .q-field__control) {
  background-color: #f8f9fa;
}

.payment-menu-item :deep(.q-item) {
  padding: 8px 16px;
  border: 1px solid transparent;
  border-radius: 4px;
}

.payment-menu-item:hover :deep(.q-item),
.payment-menu-item :deep(.q-item:hover) {
  border: 1px dashed #cbd5e1;
  border-radius: 4px;
  background-color: transparent;
}

.payment-method-card :deep(.q-card-section) {
  padding: 0.75rem !important;
}

.space-y-4 > * + * {
  margin-top: 1rem;
}
</style>
